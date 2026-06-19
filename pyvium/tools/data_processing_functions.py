import os
import csv
from typing import Dict, List, Union
from tqdm import tqdm

from ..util import get_file_list


class DataProcessing:
    @staticmethod
    def _extract_data_section(lines: List[str], start_index: int) -> List[List[float]]:
        """Extracts a section of data from a list of lines starting at the given index."""
        if not lines or start_index >= len(lines):
            raise ValueError("Invalid input parameters")
        try:
            section_data = []
            num_points = int(lines[start_index + 2].strip().replace('\x00', ''))
            start = start_index + 3
            end = start + num_points
            for line_index in range(start, end):
                row = lines[line_index].split()
                datapoint = [float(value) for value in row]
                section_data.append(datapoint)
            return section_data
        except ValueError as e:
            print(f"Warning: Could not parse data section. Error: {e}")
            return []

    @staticmethod
    def export_to_csv(data, file_path) -> None:
        """Saves the given data to a CSV file at the specified file path."""
        path = os.path.normpath(file_path)
        # newline="" so csv.writer controls line endings (avoids blank lines on Windows).
        with open(path, "w", encoding="UTF-8", newline="") as f:
            write = csv.writer(f)
            write.writerows(data)

    @staticmethod
    def get_idf_data(idf_path: str) -> List[List[float]]:
        """Extracts primary data from an IDF file and returns it as a list."""
        data = []

        # open and read idf file
        with open(idf_path, "r", encoding="ISO-8859-2") as idf:
            raw_data = idf.read()

        # split the file into a list of lines
        lines = raw_data.splitlines()

        for index, line in enumerate(lines):
            if "primary_data" in line:
                data.extend(DataProcessing._extract_data_section(lines, index))

        return data
        
    @staticmethod
    def get_all_idf_data(idf_path: str) -> Dict[str, List[List[float]]]:
        """Extracts all data (primary and extra measurement data) from an IDF file and returns it as a dictionary."""
        data = {"primary_data": []}

        # open and read idf file
        with open(idf_path, "r", encoding="ISO-8859-2") as idf:
            raw_data = idf.read()

        # split the file into a list of lines
        lines = raw_data.splitlines()

        def extract_osc_data(lines, start_index: int) -> List[List[float]]:
            try:
                section_data = []
                num_sections = int(lines[start_index + 1].strip().replace('\x00', ''))
                start = start_index + 1
                for _ in range(num_sections):
                    section = DataProcessing._extract_data_section(lines, int(start))
                    section_data.append(section)
                    num_points = int(lines[start + 2])
                    start = start + 2 + num_points
                return section_data
            except ValueError as e:
                print(f"Warning: Could not parse osc_data section. Error: {e}")
                return []

        for index, line in enumerate(lines):
            if "primary_data" in line:
                data["primary_data"].extend(DataProcessing._extract_data_section(lines, index))
            elif "ocpdata" in line:
                data["ocpdata"] = DataProcessing._extract_data_section(lines, index)
            elif "pretreatmentdata" in line:
                data["pretreatmentdata"] = DataProcessing._extract_data_section(lines, index)
            elif "RsCs_data" in line:
                data["RsCs_data"] = DataProcessing._extract_data_section(lines, index)
            elif "osc_data" in line:
                data["osc_data"] = extract_osc_data(lines, index)

        return data

    @staticmethod
    def convert_idf_to_csv(idf_path) -> None:
        """Extracts the data from a ivium .idf file and saves the data to a .csv file"""
        path = os.path.normpath(rf"{idf_path}")
        data = DataProcessing.get_idf_data(path)
        DataProcessing.export_to_csv(data, path + ".csv")

    @staticmethod
    def convert_idf_dir_to_csv(idf_dir_path=".") -> Dict[str, Union[int, List[str]]]:
        """Extracts the data of all .idf files on a directory and saves the data .csv files"""
        path = os.path.normpath(idf_dir_path)
        files = get_file_list(path)
        idf_files = list(filter(lambda file: file.endswith(".idf"), files))
        converted_count = 0
        errors = []
        for idf_filename in tqdm(idf_files):
            try:
                DataProcessing.convert_idf_to_csv(path + "\\" + idf_filename)
                converted_count += 1
            except Exception:
                errors.append(idf_filename)

        return {
            "converted_count": converted_count,
            "error_count": len(errors),
            "errors": errors,
        }
