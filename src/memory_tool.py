"""
LocalFilesystemMemoryTool: A file-based memory backend for Claude

This implementation extends BetaAbstractMemoryTool to provide persistent memory
storage using the local filesystem. Claude can autonomously create, read, update,
and delete memory files within the /memories directory.

For production use with security considerations, see:
https://docs.claude.com/en/docs/agents-and-tools/tool-use/memory-tool
"""

import logging
from pathlib import Path
from typing import Optional, List
import shutil
from typing_extensions import override

from anthropic.lib.tools import BetaAbstractMemoryTool
from anthropic.types.beta import (
    BetaMemoryTool20250818ViewCommand,
    BetaMemoryTool20250818CreateCommand,
    BetaMemoryTool20250818DeleteCommand,
    BetaMemoryTool20250818InsertCommand,
    BetaMemoryTool20250818RenameCommand,
    BetaMemoryTool20250818StrReplaceCommand,
)


logger = logging.getLogger(__name__)


class LocalFilesystemMemoryTool(BetaAbstractMemoryTool):
    """
    File-based memory implementation for Claude's memory tool.

    Stores memories as plain text files in a dedicated directory.
    Claude autonomously decides when to create, read, update, or delete memories.
    """

    def __init__(self, base_path: str = "./memory"):
        """
        Initialize the memory tool with a storage directory.

        Args:
            base_path: Base directory for storing memory files
        """
        super().__init__()
        self.base_path = Path(base_path)
        self.memory_root = self.base_path / "memories"
        self.memory_root.mkdir(exist_ok=True, parents=True)
        logger.info(f"[MEMORY] Initialized with root: {self.memory_root.absolute()}")

    def _validate_path(self, path: str) -> Path:
        """
        Validate that a path is within the memory directory.

        NOTE: For simplicity, this implementation does basic path validation.
        For production use with untrusted input, implement robust path traversal
        protection. See: https://docs.claude.com/en/docs/agents-and-tools/tool-use/memory-tool#security

        Args:
            path: Path within /memories (e.g., "/memories/user_profile.txt")

        Returns:
            Resolved absolute path

        Raises:
            ValueError: If path attempts to escape memory directory
        """
        if not path.startswith("/memories"):
            raise ValueError(f"Path must start with /memories, got: {path}")

        # Remove /memories prefix
        relative_path = path[len("/memories"):].lstrip("/")
        full_path = self.memory_root / relative_path if relative_path else self.memory_root

        # Validate path stays within memory directory
        try:
            full_path.resolve().relative_to(self.memory_root.resolve())
        except ValueError as e:
            raise ValueError(f"Path {path} would escape /memories directory") from e

        return full_path

    @override
    def view(self, command: BetaMemoryTool20250818ViewCommand) -> str:
        """
        View contents of a memory file or list directory contents.

        Args:
            command: View command with path and optional view_range

        Returns:
            File contents or directory listing
        """
        logger.debug(f"[MEMORY] view() called: path={command.path}, view_range={command.view_range}")

        try:
            full_path = self._validate_path(command.path)

            # Directory listing
            if full_path.is_dir():
                items: List[str] = []
                try:
                    for item in sorted(full_path.iterdir()):
                        if item.name.startswith("."):
                            continue
                        items.append(f"{item.name}/" if item.is_dir() else item.name)
                    result = f"Directory: {command.path}\n" + "\n".join([f"- {item}" for item in items])
                    logger.debug(f"[MEMORY] Listed directory: {command.path} - Found {len(items)} items")
                    return result
                except Exception as e:
                    raise RuntimeError(f"Cannot read directory {command.path}: {e}") from e

            # File reading
            if not full_path.is_file():
                raise RuntimeError(f"Path {command.path} does not exist")

            content = full_path.read_text(encoding='utf-8')
            lines = content.splitlines()

            # Apply line range if specified
            view_range = command.view_range
            if view_range:
                start_line = max(1, view_range[0]) - 1
                end_line = len(lines) if view_range[1] == -1 else view_range[1]
                lines = lines[start_line:end_line]

            result = '\n'.join(lines)

            # Log content that was loaded
            logger.debug(f"[MEMORY] Loaded file: {command.path}")
            logger.debug(f"[MEMORY]   Lines: {len(lines)} | Characters: {len(result)}")
            if len(result) <= 200:
                logger.debug(f"[MEMORY]   Content: {result}")
            else:
                logger.debug(f"[MEMORY]   Content preview: {result[:200]}... (truncated)")

            return result

        except (ValueError, RuntimeError) as e:
            logger.warning(f"[MEMORY] Error in view: {e}")
            raise
        except Exception as e:
            logger.error(f"[MEMORY] Unexpected error viewing {command.path}: {e}")
            raise RuntimeError(f"Error viewing {command.path}: {e}") from e

    @override
    def create(self, command: BetaMemoryTool20250818CreateCommand) -> str:
        """
        Create a new memory file with content.

        Args:
            command: Create command with path and file_text

        Returns:
            Success message
        """
        logger.debug(f"[MEMORY] create() called: path={command.path}")

        try:
            full_path = self._validate_path(command.path)

            if full_path.exists():
                raise RuntimeError(f"File already exists: {command.path}. Use str_replace or insert to modify.")

            # Create parent directories if needed
            full_path.parent.mkdir(parents=True, exist_ok=True)

            full_path.write_text(command.file_text, encoding='utf-8')

            # Log the new file creation with content
            lines = command.file_text.splitlines()
            logger.debug(f"[MEMORY] Created new file: {command.path}")
            logger.debug(f"[MEMORY]   Lines: {len(lines)} | Characters: {len(command.file_text)}")
            if len(command.file_text) <= 200:
                logger.debug(f"[MEMORY]   Content: {command.file_text}")
            else:
                logger.debug(f"[MEMORY]   Content preview: {command.file_text[:200]}... (truncated)")

            logger.info(f"[MEMORY] ✓ Created memory file: {command.path}")
            return f"Successfully created {command.path}"

        except (ValueError, RuntimeError) as e:
            logger.warning(f"[MEMORY] Error in create: {e}")
            raise
        except Exception as e:
            logger.error(f"[MEMORY] Unexpected error creating {command.path}: {e}")
            raise RuntimeError(f"Error creating {command.path}: {e}") from e

    @override
    def str_replace(self, command: BetaMemoryTool20250818StrReplaceCommand) -> str:
        """
        Replace a string in a memory file.

        Args:
            command: StrReplace command with path, old_str, and new_str

        Returns:
            Success message
        """
        logger.debug(f"[MEMORY] str_replace() called: path={command.path}")

        try:
            full_path = self._validate_path(command.path)

            if not full_path.is_file():
                raise RuntimeError(f"File not found: {command.path}")

            content = full_path.read_text(encoding='utf-8')

            # Verify old_str appears exactly once
            count = content.count(command.old_str)
            if count == 0:
                raise RuntimeError(f"String not found in {command.path}")
            elif count > 1:
                raise RuntimeError(f"String appears {count} times in {command.path}. Must be unique.")

            new_content = content.replace(command.old_str, command.new_str)
            full_path.write_text(new_content, encoding='utf-8')

            # Log what was changed
            old_preview = command.old_str if len(command.old_str) <= 100 else command.old_str[:100] + "..."
            new_preview = command.new_str if len(command.new_str) <= 100 else command.new_str[:100] + "..."
            logger.debug(f"[MEMORY] Updated file: {command.path}")
            logger.debug(f"[MEMORY]   Old text: {old_preview}")
            logger.debug(f"[MEMORY]   New text: {new_preview}")
            logger.info(f"[MEMORY] ✓ Replaced string in {command.path}")

            return f"Successfully replaced string in {command.path}"

        except (ValueError, RuntimeError) as e:
            logger.warning(f"[MEMORY] Error in str_replace: {e}")
            raise
        except Exception as e:
            logger.error(f"[MEMORY] Unexpected error in str_replace {command.path}: {e}")
            raise RuntimeError(f"Error replacing string in {command.path}: {e}") from e

    @override
    def insert(self, command: BetaMemoryTool20250818InsertCommand) -> str:
        """
        Insert text at a specific line number.

        Args:
            command: Insert command with path, line, and insert_line

        Returns:
            Success message
        """
        logger.debug(f"[MEMORY] insert() called: path={command.path}, line={command.line}")

        try:
            full_path = self._validate_path(command.path)

            if not full_path.is_file():
                raise RuntimeError(f"File not found: {command.path}")

            content = full_path.read_text(encoding='utf-8')
            lines = content.splitlines(keepends=True)

            # Convert 1-indexed to 0-indexed
            insert_idx = command.line - 1

            if insert_idx < 0 or insert_idx > len(lines):
                raise RuntimeError(f"Line {command.line} is out of range (file has {len(lines)} lines)")

            # Ensure insert_line ends with newline
            insert_text = command.insert_line
            if not insert_text.endswith('\n'):
                insert_text += '\n'

            lines.insert(insert_idx, insert_text)
            full_path.write_text(''.join(lines), encoding='utf-8')

            # Log what was inserted
            insert_preview = command.insert_line if len(command.insert_line) <= 100 else command.insert_line[:100] + "..."
            logger.debug(f"[MEMORY] Updated file: {command.path}")
            logger.debug(f"[MEMORY]   Inserted at line {command.line}: {insert_preview}")
            logger.info(f"[MEMORY] ✓ Inserted line at position {command.line} in {command.path}")

            return f"Successfully inserted line in {command.path}"

        except (ValueError, RuntimeError) as e:
            logger.warning(f"[MEMORY] Error in insert: {e}")
            raise
        except Exception as e:
            logger.error(f"[MEMORY] Unexpected error inserting line in {command.path}: {e}")
            raise RuntimeError(f"Error inserting line in {command.path}: {e}") from e

    @override
    def delete(self, command: BetaMemoryTool20250818DeleteCommand) -> str:
        """
        Delete a memory file or directory.

        Args:
            command: Delete command with path

        Returns:
            Success message
        """
        logger.debug(f"[MEMORY] delete() called: path={command.path}")

        try:
            full_path = self._validate_path(command.path)

            if not full_path.exists():
                raise RuntimeError(f"Path not found: {command.path}")

            if full_path.is_dir():
                shutil.rmtree(full_path)
                logger.debug(f"[MEMORY] Deleted directory: {command.path}")
                logger.info(f"[MEMORY] ✓ Deleted directory: {command.path}")
                return f"Successfully deleted directory {command.path}"
            else:
                full_path.unlink()
                logger.debug(f"[MEMORY] Deleted file: {command.path}")
                logger.info(f"[MEMORY] ✓ Deleted file: {command.path}")
                return f"Successfully deleted {command.path}"

        except (ValueError, RuntimeError) as e:
            logger.warning(f"[MEMORY] Error in delete: {e}")
            raise
        except Exception as e:
            logger.error(f"[MEMORY] Unexpected error deleting {command.path}: {e}")
            raise RuntimeError(f"Error deleting {command.path}: {e}") from e

    @override
    def rename(self, command: BetaMemoryTool20250818RenameCommand) -> str:
        """
        Rename or move a memory file.

        Args:
            command: Rename command with old_path and new_path

        Returns:
            Success message
        """
        logger.debug(f"[MEMORY] rename() called: old_path={command.old_path}, new_path={command.new_path}")

        try:
            full_old_path = self._validate_path(command.old_path)
            full_new_path = self._validate_path(command.new_path)

            if not full_old_path.exists():
                raise RuntimeError(f"File not found: {command.old_path}")

            if full_new_path.exists():
                raise RuntimeError(f"Destination already exists: {command.new_path}")

            # Create parent directories if needed
            full_new_path.parent.mkdir(parents=True, exist_ok=True)

            full_old_path.rename(full_new_path)

            logger.debug(f"[MEMORY] Renamed/moved: {command.old_path} → {command.new_path}")
            logger.info(f"[MEMORY] ✓ Renamed {command.old_path} to {command.new_path}")
            return f"Successfully renamed {command.old_path} to {command.new_path}"

        except (ValueError, RuntimeError) as e:
            logger.warning(f"[MEMORY] Error in rename: {e}")
            raise
        except Exception as e:
            logger.error(f"[MEMORY] Unexpected error renaming {command.old_path}: {e}")
            raise RuntimeError(f"Error renaming {command.old_path}: {e}") from e

    def clear_all_memory(self) -> str:
        """
        Delete all memory files (useful for debugging/testing).

        Returns:
            Success message
        """
        logger.warning("[MEMORY] clear_all_memory() called - deleting all memories")

        try:
            if self.memory_root.exists():
                shutil.rmtree(self.memory_root)
                self.memory_root.mkdir(exist_ok=True)

            logger.info("[MEMORY] ✓ All memories cleared")
            return "All memories have been cleared"

        except Exception as e:
            logger.error(f"[MEMORY] Error clearing memories: {e}")
            return f"Error clearing memories: {str(e)}"
