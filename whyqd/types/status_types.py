from enum import Enum


class StatusType(str, Enum):
    WAITING = "waiting"
    PROCESSING = "processing"
    READY_MERGE = "ready_merge"
    READY_STRUCTURE = "ready_structure"
    READY_CATEGORY = "ready_categorise"
    READY_FILTER = "ready_filter"
    READY_TRANSFORM = "ready_transform"
    CREATE_ERROR = "create_error"
    MERGE_ERROR = "merge_error"
    STRUCTURE_ERROR = "structure_error"
    CATEGORY_ERROR = "category_error"
    TRANSFORM_ERROR = "transform_error"
    PROCESS_COMPLETE = "process_complete"

    def describe(self):
        description = {
            "waiting": "Waiting ...",
            "processing": "Processing ...",
            "ready_merge": "Ready to Merge",
            "ready_structure": "Ready to Structure",
            "ready_categorise": "Ready to Categorise",
            "ready_filter": "Ready to Filter",
            "ready_transform": "Ready to Transform",
            "create_error": "Create Error",
            "merge_error": "Merge Error",
            "structure_error": "Structure Error",
            "category_error": "Categorisation Error",
            "transform_error": "Transform Error",
            "process_complete": "Process Complete",
        }
        return description[self.value]
