"""Agent Skills discovery, activation, and bounded reference loading."""
from pathlib import Path
import hashlib
import re
import yaml


class SkillRegistry:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.entries = {}
        for path in sorted(self.root.glob("*/SKILL.md")):
            if not path.resolve().is_relative_to(self.root):
                raise ValueError("Skill symlinks cannot leave the skill root")
            text = path.read_text(encoding="utf-8")
            parts = text.split("---", 2)
            if len(parts) != 3 or parts[0].strip():
                raise ValueError(f"Invalid skill frontmatter: {path.parent.name}")
            meta = yaml.safe_load(parts[1])
            if not isinstance(meta, dict):
                raise ValueError("Skill metadata must be a mapping")
            name, description = meta.get("name", ""), meta.get("description", "")
            if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name) or len(name) > 64 or name != path.parent.name:
                raise ValueError("Invalid skill name")
            if not isinstance(description, str) or not 1 <= len(description) <= 1024:
                raise ValueError("Invalid skill description")
            self.entries[name] = {"name": name, "description": description, "path": path,
                                  "version": hashlib.sha256(text.encode()).hexdigest()}

    def discover(self):
        return [{k: v for k, v in entry.items() if k != "path"} for entry in self.entries.values()]

    def activate(self, name):
        entry = self.entries[name]
        text = entry["path"].read_text(encoding="utf-8")
        if hashlib.sha256(text.encode()).hexdigest() != entry["version"]:
            raise ValueError("Skill changed during execution; start a new run")
        return {"name": name, "version": entry["version"], "instructions": text.split("---", 2)[2].strip()}

    def resource(self, name, relative_path):
        root = self.entries[name]["path"].parent.resolve()
        path = (root / relative_path).resolve()
        if not path.is_relative_to(root) or path.suffix != ".md" or not path.is_file():
            raise ValueError("Only Markdown resources inside the selected skill are allowed")
        if path.stat().st_size > 32768:
            raise ValueError("Skill reference is too large")
        text = path.read_text(encoding="utf-8")
        return {"content": text, "version": hashlib.sha256(text.encode()).hexdigest()}
