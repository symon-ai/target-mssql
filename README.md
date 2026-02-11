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
| keep_out_of_bound_dates   |  False   |  False  | Convert pandas out-of-bound dates to MSSQL limits (min: 1753-01-01, max: 9999-12-31 23:59:59.997)                                          |
| stream_maps               |  False   |  None   | Config object for stream maps capability. For more information check out [Stream Maps](https://sdk.meltano.com/en/latest/stream_maps.html). |
| stream_map_config         |  False   |  None   | User-defined config values to be used within map expressions.                                                                               |
| flattening_enabled        |  False   |  None   | 'True' to enable schema flattening and automatically expand nested properties.                                                              |
| flattening_max_depth      |  False   |  None   | The max depth to flatten schemas.                                                                                                           |

### Executing the Target Directly

```bash
cat /path/to/row-file | target-mssql --config config.json
```

## Package manager

We only use poetry to manage our packages. Pipfile is there because our code scan doesn't support poetry.lock. So we do the following hack to generate Pipfile and Pipfile.lock based on our poetry.lock:
### 1. Export all dependencies from poetry.lock to requirements.txt
```
poetry export -f requirements.txt --output requirements.txt --without-hashes
```
### 1b. (Optional) Make sure pipenv has the right python version
Check:
```
pipenv --support
```
Install:
```
python -m pip install --user pipenv
```

# 2. Generate Pipfile and Pipfile.lock from requirements.txt (make sure you pass in right version of python)
```
pipenv install --python 3.13 -r requirements.txt
```

Check that the required python version in the Pipfile matches your expected python version. For some reason even if requirements.txt specify the right python version pipenv can still default to a different version based on the some stale versioning in the venv. In which case, do the following:

### 1. Delete the Pipfile and lock, and deactivate your venv

### 2. Delete the venv with `pipenv --rm`

### 3. Re-run the pipenv install command

## SDK Dev Guide

See the [dev guide](https://sdk.meltano.com/en/latest/dev_guide.html) for more instructions on how to use the Meltano SDK to
develop your own Singer taps and targets.
