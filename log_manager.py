# app_logger.py
import csv
from datetime import datetime
from typing import List, Union, Optional, Any, Tuple, Dict # Added Dict

class AppLogger:
    """
    Manages the logging of application data to a CSV file.
    """
    def __init__(self):
        self._logging = False
        self._log_file = None
        self._csv_writer = None
        self._log_filename = ""
        # Stores (key_name, header_name, formatter_string) tuples in the order they should appear
        self._column_definitions: List[Tuple[str, str, str]] = []

    @property
    def is_logging(self) -> bool:
        """Returns True if logging is currently active, False otherwise."""
        return self._logging

    @property
    def filename(self) -> str:
        """Returns the current log filename."""
        return self._log_filename

    def start_logging(self, filename: str, columns_config: Optional[List[Tuple[str, str, str]]] = None) -> bool:
        """
        Starts the logging process to the specified CSV file.
        'columns_config' should be a list of (key_name, header_name, formatter_string) tuples.
        The 'Timestamp' column is automatically added at the beginning.
        Returns True on success, False on failure.
        """
        if self._logging:
            print("Logging is already active.")
            return True

        if not filename.strip():
            print("Log filename cannot be empty.")
            return False

        if not filename.endswith(".csv"):
            filename += ".csv"
        self._log_filename = filename

        try:
            header_names = ["Timestamp"] # Timestamp is always the first column
            self._column_definitions = [] # Reset definitions

            if columns_config:
                # Store the full column definitions for later use in log_data
                self._column_definitions = columns_config
                for key_name, header_name, _ in columns_config:
                    header_names.append(header_name)
            else:
                print("Warning: No column configuration provided for logging. Using generic default.")
                # Provide a generic default if no config is given.
                # Note: For true dynamism, you might want to force columns_config.
                self._column_definitions = [
                    ("value1", "Value1", ""), ("value2", "Value2", ""), ("value3", "Value3", "")
                ]
                for key_name, header_name, _ in self._column_definitions:
                    header_names.append(header_name)

            self._log_file = open(filename, 'w', newline='')
            self._csv_writer = csv.writer(self._log_file)
            self._csv_writer.writerow(header_names) # Write the combined header

            self._logging = True
            print(f"Logging started to: {self._log_filename}")
            return True
        except Exception as e:
            print(f"Error starting log: {e}")
            self.stop_logging() # Ensure cleanup on failure
            return False

    def stop_logging(self):
        """Stops the logging process and closes the log file."""
        if self._logging and self._log_file:
            try:
                self._log_file.close()
                print(f"Logging stopped. File saved: {self._log_filename}")
            except Exception as e:
                print(f"Error closing log file: {e}")
            finally:
                self._log_file = None
                self._csv_writer = None
                self._column_definitions = [] # Clear definitions on stop
        self._logging = False
        self._log_filename = ""

    def log_data(self, data_dict: Dict[str, Any]):
        """
        Logs a single row of data to the CSV file if logging is active.
        'data_dict' should be a dictionary where keys are the 'key_name'
        from the columns_config and values are the raw data for that column.
        """
        if not self._logging or not self._csv_writer:
            return

        try:
            formatted_row_data = [datetime.now().isoformat()] # Start with timestamp

            for key_name, _, formatter_str in self._column_definitions:
                value = data_dict.get(key_name) # Get value by key name
                
                if value is None:
                    formatted_value = "" # Or "N/A", "None", etc.
                else:
                    try:
                        # Apply f-string-like formatting
                        formatted_value = f"{value:{formatter_str}}" if formatter_str else str(value)
                    except (ValueError, TypeError):
                        # Fallback if formatting fails (e.g., trying to format string as float)
                        formatted_value = str(value)
                formatted_row_data.append(formatted_value)
            
            self._csv_writer.writerow(formatted_row_data)
            self._log_file.flush()
        except Exception as e:
            print(f"Error writing data to log file: {e}")