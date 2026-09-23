from __future__ import annotations

from .base import Detector
from .infrastructure import InfrastructureDetector
from .javascript import JavaScriptDetector
from .languages import LanguageDetector
from .php import PhpDetector
from .python import PythonDetector
from .ruby import RubyDetector


def default_detectors() -> list[Detector]:
    return [
        LanguageDetector(),
        JavaScriptDetector(),
        PhpDetector(),
        PythonDetector(),
        RubyDetector(),
        InfrastructureDetector(),
    ]
