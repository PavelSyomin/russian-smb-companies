import pathlib
import shutil
import tempfile

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.types import StructType


class SparkStage:
    SPARK_APP_NAME = "Generic Spark Stage"

    def __init__(self):
        self._session = None

        self._init_spark()

    def __del__(self):
        print("Stopping Spark")
        self._session.stop()

    def _init_spark(self):
        """Spark configuration and initialization"""
        print("Starting Spark")
        self._session = (
            SparkSession
            .builder
            .master("local")
            .appName(self.SPARK_APP_NAME)
            .getOrCreate()
        )

        web_url = self._session.sparkContext.uiWebUrl
        print(f"Spark session has started. You can monitor it at {web_url}")

    def _read(self, in_path: str, schema: StructType) -> DataFrame:
        path = pathlib.Path(in_path)
        if not path.exists():
            print(f"Input path {in_path} not found")
            return None

        if path.is_dir():
            input_files = [str(fn) for fn in path.glob("data-*.csv")]
        elif path.suffix == "csv":
            input_files = [str(path)]
        else:
            input_files = []

        if len(input_files) == 0:
            print("Input path does not contain readable CSV file(s)")
            return None

        data = self._session.read.options(
            header=True, dateFormat="dd.MM.yyyy", escape='"'
        ).schema(schema).csv(input_files)

        print(f"Source CSV contains {data.count()} rows")

        return data

    def _write(self, df: DataFrame, out_file: str):
        """Save Spark dataframe into a single CSV file"""
        with tempfile.TemporaryDirectory() as out_dir:
            options = dict(header=True, nullValue="NA", escape='"')
            df.coalesce(1).write.options(**options).csv(out_dir, mode="overwrite")

            # Spark writes to a folder with an arbitrary filename,
            # so we need to find and move the resulting file to the destination
            result = next(pathlib.Path(out_dir).glob("*.csv"), None)
            if result is None:
                print("Failed to save file")

            pathlib.Path(out_file).parent.mkdir(parents=True, exist_ok=True)
            shutil.move(result, out_file)
