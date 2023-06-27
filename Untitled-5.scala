import org.apache.spark.sql.SparkSession

object SparkSQLExample {
  def main(args: Array[String]): Unit = {
    // Create a SparkSession
    val spark = SparkSession.builder()
      .appName("SparkSQLExample")
      .master("local[*]")
      .getOrCreate()
      
    // Import implicit conversions for DataFrame operations
    import spark.implicits._
    
    // Define the schema for a sample DataFrame
    val schema = "name STRING, age INT, city STRING"
    
    // Create a sample DataFrame with some data
    val data = Seq(
      ("Alice", 28, "New York"),
      ("Bob", 32, "San Francisco"),
      ("Charlie", 25, "Chicago")
    )
    
    // Convert the data to a DataFrame
    val df = spark.createDataFrame(data).toDF(schema.split(",\\s*"): _*)
    
    // Register the DataFrame as a temporary view
    df.createOrReplaceTempView("people")
    
    // Execute a SQL query using Spark SQL
    val result = spark.sql("SELECT name, age FROM people WHERE age >= 30")
    
    // Show the result
    result.show()
    
    // Stop the SparkSession
    spark.stop()
  }
}
