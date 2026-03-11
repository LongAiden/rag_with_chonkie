from pathlib import Path
from typing import Optional

from ingestion.processors.pdf_parser_base import PDFParserBase
from ingestion.processors.pdf_to_markdown import PDFToMarkdownConverter, ConversionOptions
from ingestion.processors.vlm_extractor import OllamaVLMExtractor


class OllamaPDFParser(PDFParserBase):
    """
    Wraps PDFToMarkdownConverter + OllamaVLMExtractor.
    Zero behaviour change — existing logic untouched.
    """

    def __init__(
        self,
        ollama_base_url: str,
        ollama_model: str,
        use_vlm: bool = True,
    ):
        vlm = OllamaVLMExtractor(base_url=ollama_base_url, model_name=ollama_model) if use_vlm else None
        self._converter = PDFToMarkdownConverter(default_options=ConversionOptions(vlm_extractor=vlm))

    def get_backend_name(self) -> str:
        return "ollama"

    def parse_pdf(self, path: str | Path, output_path: Optional[str | Path] = None) -> str:
        return self._converter.convert(source=path, output=output_path)
