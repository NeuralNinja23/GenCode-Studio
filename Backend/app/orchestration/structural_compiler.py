# app/orchestration/structural_compiler.py

from typing import Dict
from pathlib import Path


class StructuralViolation(Exception):
    pass


class StructuralCompiler:
    """
    Authoritative structural validator.
    If this fails, the branch MUST fail.
    """

    REQUIRED_BACKEND_DIRS = [
        "backend/app",
    ]

    REQUIRED_FRONTEND_DIRS = [
        "frontend",
    ]

    REQUIRED_BACKEND_FILES = [
        "backend/app/main.py",
    ]

    REQUIRED_ROUTER_HINT = "backend/app/routers"

    @classmethod
    def validate(cls, files: Dict[str, str]):
        paths = {Path(p).as_posix() for p in files.keys()}

        cls._validate_directories(paths)
        cls._validate_required_files(paths)
        cls._validate_backend_routes(paths)
        cls._validate_frontend_presence(paths)

    @classmethod
    def _validate_directories(cls, paths: set[str]):
        for required in cls.REQUIRED_BACKEND_DIRS:
            if not any(p.startswith(required) for p in paths):
                raise StructuralViolation(
                    f"Missing backend directory: {required}"
                )

    @classmethod
    def _validate_required_files(cls, paths: set[str]):
        for file in cls.REQUIRED_BACKEND_FILES:
            if file not in paths:
                raise StructuralViolation(
                    f"Missing required backend file: {file}"
                )

    @classmethod
    def _validate_backend_routes(cls, paths: set[str]):
        has_router = any(
            p.startswith(cls.REQUIRED_ROUTER_HINT)
            and p.endswith(".py")
            for p in paths
        )

        if not has_router:
            raise StructuralViolation(
                "No backend router files detected (expected at least one router)"
            )

    @classmethod
    def _validate_frontend_presence(cls, paths: set[str]):
        has_frontend = any(
            p.startswith("frontend/")
            for p in paths
        )

        if not has_frontend:
            raise StructuralViolation(
                "Frontend directory missing or empty"
            )
