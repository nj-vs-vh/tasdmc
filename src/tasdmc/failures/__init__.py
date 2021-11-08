"""failures module provide failure management tools: visualization, inspection, cleanup, etc"""


from .total_cleanup import delete_all_files_from_failed_pipeline


__all__ = ['delete_all_files_from_failed_pipeline']
