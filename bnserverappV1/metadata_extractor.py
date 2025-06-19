import re
import json
from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Any, Union
import os

class MetadataExtractor(ABC):
    """Abstract base class for metadata extractors."""

    @abstractmethod
    def get_nodes(self, file_path: str) -> List[Tuple[str, str]]:
        pass

    @abstractmethod
    def format_metadata(self, node: Tuple[str, str]) -> Dict[str, Any]:
        pass

    def get_metadata_for_network(self, filename: str) -> str:
        nodes = self.get_nodes(filename)
        data = {node[0]: self.format_metadata(node) for node in nodes}
        return json.dumps(data, indent=4)

class NetMetadataExtractor(MetadataExtractor):
    """Extractor for .net format files."""

    def get_nodes(self, file_path: str) -> List[Tuple[str, str]]:
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()
        return re.findall(r"node\s+(\w+)\s*\{(.*?)\}", content, re.DOTALL)

    def format_metadata(self, node: Tuple[str, str]) -> Dict[str, Any]:
        metadata = {}
        pattern = r'(\w+)\s*=\s*(\([^)]+\)|"[^"]+"|\S+);'
        matches = re.findall(pattern, node[1])

        def convert_value(value: str) -> Union[int, float, List, str]:
            value = value.strip('"')

            if value.startswith("(") and value.endswith(")"):
                value_list = value[1:-1].split()
                return [convert_value(v) for v in value_list]

            if re.fullmatch(r"-?\d+", value):
                return int(value)
            elif re.fullmatch(r"-?\d+\.\d+", value):
                return float(value)

            return value

        for key, value in matches:
            metadata[key] = convert_value(value)

        return metadata

class BifMetadataExtractor(MetadataExtractor):
    """Extractor for .bif format files."""

    def get_nodes(self, file_path: str) -> List[Tuple[str, str]]:
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()
        return re.findall(r"variable\s+(\w+)\s*\{(.*?)\}", content, re.DOTALL)

    def format_metadata(self, node: Tuple[str, str]) -> Dict[str, Any]:
        metadata = {}
        content = node[1]

        states_match = re.search(r'type discrete.*?\{([^}]+)', content)
        if states_match:
            states_str = states_match.group(1)
            states = [state.strip() for state in states_str.split(',')]
            metadata['states'] = states

        return metadata

def get_metadata_extractor(file_extension: str) -> MetadataExtractor:
    """Factory function to get the appropriate metadata extractor."""
    extractors = {
        '.net': NetMetadataExtractor(),
        '.bif': BifMetadataExtractor(),
    }

    if file_extension not in extractors:
        raise ValueError(f"Unsupported file format: {file_extension}")

    return extractors[file_extension]

def get_metadata_for_network(filename: str) -> str:
    """Get metadata for a network file, automatically detecting the format."""
    file_extension = os.path.splitext(filename)[1].lower()
    extractor = get_metadata_extractor(file_extension)
    return extractor.get_metadata_for_network(filename)