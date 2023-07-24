# target-mssql

`target-mssql` is a Singer target for Microsoft SQL Server databases.

Build with the [Meltano Target SDK](https://sdk.meltano.com).

## Known limitations

- Objects and arrays are converted to strings, as writing json/arrays isn't supported in the underlying library that is used.
- Does not handle encoded strings

## Configuration

## Accepted Config Options

Regarding connection info, either the `sqlalchemy_url` or `username`, `password`, `host`, and `database` needs to be specified. If the `sqlalchemy_url` is set, the other connection parameters are ignored.

## Capabilities

- `about`
- `stream-maps`
- `schema-flattening`

## Settings

| Setting                   | Required | Default | Description                                                                                                                                 |
| :------------------------ | :------: | :-----: | :------------------------------------------------------------------------------------------------------------------------------------------ |
| sqlalchemy_url            |  False   |  None   | SQLAlchemy connection string                                                                                                                |
| username                  |   True   |  None   | SQL Server username                                                                                                                         |
| password                  |   True   |  None   | SQL Server password                                                                                                                         |
| host                      |   True   |  None   | SQL Server host                                                                                                                             |
| port                      |   True   |  1433   | SQL Server port (string)                                                                                                                    |
| database                  |   True   |  None   | SQL Server database                                                                                                                         |
| default_target_schema     |  False   |  None   | Default target schema to write to                                                                                                           |
| table_name                |   True   |  None   | Target table name, can include schema name e.g. dbo.table_name or just table_name                                                           |
| prefer_float_over_numeric |  False   |    0    | Use float data type for numbers (otherwise number type is used)                                                                             |
| stream_maps               |  False   |  None   | Config object for stream maps capability. For more information check out [Stream Maps](https://sdk.meltano.com/en/latest/stream_maps.html). |
| stream_map_config         |  False   |  None   | User-defined config values to be used within map expressions.                                                                               |
| flattening_enabled        |  False   |  None   | 'True' to enable schema flattening and automatically expand nested properties.                                                              |
| flattening_max_depth      |  False   |  None   | The max depth to flatten schemas.                                                                                                           |

### Executing the Target Directly

```bash
cat /path/to/row-file | target-mssql --config config.json
```

## Developer Resources

Follow these instructions to contribute to this project.

### Initialize your Development Environment

```bash
poetry shell
poetry install
```

### SDK Dev Guide

See the [dev guide](https://sdk.meltano.com/en/latest/dev_guide.html) for more instructions on how to use the Meltano SDK to
develop your own Singer taps and targets.
