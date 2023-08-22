"""mssql target sink class, which handles writing streams."""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Optional

import sqlalchemy
from singer_sdk.helpers._conformers import replace_leading_digit
from singer_sdk.sinks import SQLConnector, SQLSink
from sqlalchemy import Column
import datetime
from decimal import Decimal

from target_mssql.connector import mssqlConnector
from target_mssql.utils import generate_error_message, process_error_info

if TYPE_CHECKING:
    from singer_sdk.plugin_base import PluginBase


class mssqlSink(SQLSink):
    """mssql target sink class."""

    connector_class = mssqlConnector
    MAX_SIZE_DEFAULT = 1000

    def __init__(
        self,
        target: PluginBase,
        stream_name: str,
        schema: dict,
        key_properties: list[str] | None,
        connector: SQLConnector | None = None,
    ) -> None:
        super().__init__(target, stream_name, schema, key_properties)
        self.tmp_table_name = None
        self.table_prepared = False
        self.row_count = 0
        self.error_info = None
        self.target_table_column_types = None
        # we don't take stream name from tap because it doesn't have the schema name
        # in general we want {stream_name}.{table_name} e.g. dbo.currency
        if self._config.get("table_name"):
            self.stream_name = self._config.get("table_name")
        # decimals

    # Copied purely to help with type hints
    @property
    def connector(self) -> mssqlConnector:
        """The connector object.
        Returns:
            The connector object.
        """
        return self._connector

    @property
    def schema_name(self) -> Optional[str]:
        """Return the schema name or `None` if using names with no schema part.

        Returns:
            The target schema name.
        """

        default_target_schema = self.config.get("default_target_schema", None)
        parts = self.stream_name.split("-")

        if default_target_schema:
            return default_target_schema

        if len(parts) in {2, 3}:
            # Stream name is a two-part or three-part identifier.
            # Use the second-to-last part as the schema name.
            stream_schema = self.conform_name(parts[-2], "schema")

            if stream_schema == "public":
                return "dbo"
            else:
                return stream_schema

        # Schema name not detected.
        return None

    def preprocess_record(self, record: dict, context: dict) -> dict:
        """Process incoming record and return a modified result.
        Args:
            record: Individual record in the stream.
            context: Stream partition or context dictionary.
        Returns:
            A new, processed record.
        """
        try:
            keys = record.keys()
            for key in keys:
                if type(record[key]) in [list, dict]:
                    record[key] = json.dumps(record[key], default=str)
                elif type(record[key]) is datetime.datetime:
                    record[key] = record[key].strftime("%Y-%m-%d %H:%M:%S")
                elif 'number' in self.schema['properties'][key]['type']:
                    record[key] = Decimal(record[key])
        except Exception as e:
            self.error_info = generate_error_message(e)
            raise
        finally:
            process_error_info(self.error_info, self.config)

        return record

    def bulk_insert_records(
        self,
        full_table_name: str,
        schema: dict,
        records: Iterable[Dict[str, Any]],
        is_temp_table: bool = False,
    ) -> Optional[int]:
        """Bulk insert records to an existing destination table.
        The default implementation uses a generic SQLAlchemy bulk insert operation.
        This method may optionally be overridden by developers in order to provide
        faster, native bulk uploads.
        Args:
            full_table_name: the target table name.
            schema: the JSON schema for the new table, to be used when inferring column
                names.
            records: the input records.
            is_temp_table: whether the table is a temp table.
        Returns:
            True if table exists, False if not, None if unsure or undetectable.
        """
        columns = self.column_representation(schema)

        # insert_records = []
        # we want something like ('col1_value', 'col2_value', NULL, '1.2345') in the end
        # for record in records:
        #     insert_record = '('
        #     for column in columns:
        #         if record.get(column.name) is not None:
        #             if 'number' in schema['properties'][column.name]['type']:
        #                 insert_record += f"{record.get(column.name)}, "
        #             else:
        #                 insert_record += f"'{self.string_escape_value(record.get(column.name))}', "
        #         else:
        #             # convert None to NULL
        #             insert_record += 'NULL, '
        #     insert_records.append(insert_record.rstrip(', ') + ')')

        insert_records = []
        for record in records:
            insert_record = []
            for column in columns:
                if 'number' in schema['properties'][column.name]['type']:
                    target_type = self.target_table_column_types.get(column.name)
                    # these types cannot have decimal places or we fail during insert
                    if target_type == 'int' or target_type == 'bigint' or target_type == 'bit':
                        insert_record.append(int(record.get(column.name)))
                    else:
                        insert_record.append(str(record.get(column.name)))
                else:
                    insert_record.append(record.get(column.name))
            insert_records.append(tuple(insert_record))

        insert_sql = self.generate_insert_statement(
            full_table_name,
            schema,
            insert_records
        )

        try:
            # use the underlying cursor to execute this insert for better performance
            cursor = self.connection.connection.cursor()
            cursor.fast_executemany = True
            cursor.executemany(insert_sql, insert_records)
            self.connection.connection.commit()

            self.row_count += len(records)
            self.logger.info(f'Rows processed: {self.row_count}.')
        except Exception as e:
            # pymssql error msgs are not very reader friendly
            # OperationalError - e.g. when cursor can't convert incoming data to a suitable SQL type
            msg = re.search(", b'(.*)DB-Lib", str(e))
            if msg is not None:
                self.error_info = generate_error_message(e, None, msg.group(1))
                raise
            # attempting to insert value into ID column
            msg = re.search(', b"(.*) when IDENTITY_INSERT is set to OFF', str(e))
            if msg is not None:
                self.error_info = generate_error_message(e, None, msg.group(1))
                raise
            # IntegrityError - e.g. when attempting to insert NULL into a column that cannot be NULL
            msg = re.search('b"(.*),.*; (.*)DB-Lib', str(e))
            if msg is not None:
                self.error_info = generate_error_message(e, None, f'{msg.group(1)} {msg.group(2)}')
                raise
            # unexpected error, log it and improve this message after
            self.error_info = generate_error_message(e)
            raise
        finally:
            process_error_info(self.error_info, self.config)

        if isinstance(records, list):
            return len(records)  # If list, we can quickly return record count.

        return None  # Unknown record count.

    def column_representation(
        self,
        schema: dict,
    ) -> List[Column]:
        """Returns a sql alchemy table representation for the current schema."""
        columns: list[Column] = []
        conformed_properties = self.conform_schema(schema)["properties"]
        for property_name, property_jsonschema in conformed_properties.items():
            columns.append(
                Column(
                    property_name,
                    self.connector.to_sql_type(property_jsonschema),
                )
            )
        return columns

    def process_batch(self, context: dict) -> None:
        """Process a batch with the given batch context.
        Writes a batch to the SQL target. Developers may override this method
        in order to provide a more efficient upload/upsert process.
        Args:
            context: Stream partition or context dictionary.
        """
        # First we need to be sure the main table is already created
        conformed_records = (
            [self.conform_record(record) for record in context["records"]]
            if isinstance(context["records"], list)
            else (self.conform_record(record) for record in context["records"])
        )

        join_keys = [self.conform_name(key, "column") for key in self.key_properties]
        schema = self.conform_schema(self.schema)

        if not self.table_prepared:
            self.logger.info(f"Preparing table {self.full_table_name}")
            self.connector.prepare_table(
                full_table_name=self.full_table_name,
                schema=schema,
                primary_keys=join_keys,
                as_temp_table=False,
            )
            self.table_prepared = True

        if self.tmp_table_name is None:
            # Create a temp table (Creates from the table above)
            self.logger.info(f"Creating temp table for {self.full_table_name}")
            self.connector.create_temp_table_from_table(
                from_table_name=self.full_table_name
            )

        if self.target_table_column_types is None:
            self.target_table_column_types = self.connector.get_target_table_column_types(self.full_table_name)

        db_name, schema_name, table_name = self.parse_full_table_name(
            self.full_table_name
        )
        self.tmp_table_name = (
            f"{schema_name}.#{table_name}" if schema_name else f"#{table_name}"
        )

        # Insert into temp table
        self.bulk_insert_records(
            full_table_name=self.tmp_table_name,
            schema=schema,
            records=conformed_records,
            is_temp_table=True,
        )


    def drop_and_insert_from_table(
        self,
        from_table_name: str,
        to_table_name: str
    ) -> Optional[int]:
        """Drop old table and insert new data back in.
        Args:
            from_table_name: The source table name.
            to_table_name: The destination table name.
        Return:
            The number of records copied, if detectable, or `None` if the API does not
            report number of records affected/inserted.
        """
        # first check if we have alter access, it is most efficient if we do
        if (self.connector.has_alter_permission(to_table_name)):
            sql_stmt = f"""
                SET XACT_ABORT ON;
                BEGIN TRANSACTION;
                    TRUNCATE TABLE {to_table_name};
                    INSERT INTO {to_table_name}
                    SELECT * FROM {from_table_name};
                COMMIT TRANSACTION;
            """
        else:
            sql_stmt = f"""
                SET XACT_ABORT ON;
                BEGIN TRANSACTION;
                    DELETE FROM {to_table_name};
                    INSERT INTO {to_table_name}
                    SELECT * FROM {from_table_name};
                COMMIT TRANSACTION;
            """

        with self.connection.begin():
            self.connection.execute(sql_stmt)

    def parse_full_table_name(
        self, full_table_name: str
    ) -> tuple[str | None, str | None, str]:
        """Parse a fully qualified table name into its parts.
        Developers may override this method if their platform does not support the
        traditional 3-part convention: `db_name.schema_name.table_name`
        Args:
            full_table_name: A table name or a fully qualified table name. Depending on
                SQL the platform, this could take the following forms:
                - `<db>.<schema>.<table>` (three part names)
                - `<db>.<table>` (platforms which do not use schema groupings)
                - `<schema>.<name>` (if DB name is already in context)
                - `<table>` (if DB name and schema name are already in context)
        Returns:
            A three part tuple (db_name, schema_name, table_name) with any unspecified
            or unused parts returned as None.
        """
        db_name: str | None = None
        schema_name: str | None = None

        parts = full_table_name.split(".")
        if len(parts) == 1:
            table_name = full_table_name
        if len(parts) == 2:
            schema_name, table_name = parts
        if len(parts) == 3:
            db_name, schema_name, table_name = parts

        return db_name, schema_name, table_name

    def snakecase(self, name):
        name = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        name = re.sub("([a-z0-9])([A-Z])", r"\1_\2", name)
        return name.lower()

    def conform_name(self, name: str, object_type: Optional[str] = None) -> str:
        """Conform a stream property name to one suitable for the target system.
        Transforms names to snake case by default, applicable to most common DBMSs'.
        Developers may override this method to apply custom transformations
        to database/schema/table/column names.
        Args:
            name: Property name.
            object_type: One of ``database``, ``schema``, ``table`` or ``column``.
        Returns:
            The name that ms sql would accept.
        """
        # strip non-alphanumeric characters, keeping - . _ and spaces
        name = re.sub(r"[^a-zA-Z0-9_\-\.\s]", "", name)

        return replace_leading_digit(name)

    def clean_up(self) -> None:
        """Once all rows are inserted to temp table, we replace original table with temp table data.
        """
        self.logger.info("Cleaning up %s", self.stream_name)

        if self.tmp_table_name is not None:
            self.drop_and_insert_from_table(
                from_table_name=self.tmp_table_name,
                to_table_name=self.full_table_name,
            )

    def generate_insert_statement(
        self,
        full_table_name: str,
        schema: dict,
        records: List[tuple]
    ) -> str:
        """Generate an insert statement for the given records.

        Args:
            full_table_name: the target table name.
            schema: the JSON schema for the new table.

        Returns:
            An insert statement.
        """
        property_names = list(self.conform_schema(schema)["properties"].keys())
        statement = f"""\
            INSERT INTO {full_table_name}
            ({', '.join(f'[{prop}]' for prop in property_names)})
            VALUES ({','.join('?' for _ in range(len(property_names)))})
        """
        return statement
    
    def _validate_and_parse(self, record: dict) -> dict:
        """Validate or repair the record, parsing to python-native types as needed.

        Args:
            record: Individual record in the stream.

        Returns:
            record
        """
        try:
            self._validator.validate(record)
            self._parse_timestamps_in_record(
                record=record,
                schema=self.schema,
                treatment=self.datetime_error_treatment,
            )
        except Exception as e:
            msg = re.search("(.*)\n", str(e)).group(1)
            self.error_info = generate_error_message(e, None, msg)
            raise
        finally:
            process_error_info(self.error_info, self.config)
        return record
    
    @property
    def max_size(self) -> int:
        """Get max batch size.

        Returns:
            Max number of records to batch before `is_full=True`
        """
        return self.MAX_SIZE_DEFAULT
    