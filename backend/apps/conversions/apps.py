from django.apps import AppConfig


class ConversionsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.conversions"
    label = "conversions"
    verbose_name = "Conversions"

    def ready(self):
        """
        Register all conversion engines with the global EngineRegistry.

        This runs once when Django starts. Adding a new engine is a one-liner here.
        """
        from apps.conversions.engines.registry import engine_registry
        from apps.conversions.engines.pdf_to_docx import PdfToDocxEngine
        from apps.conversions.engines.pdf_to_image import PdfToJpgEngine, PdfToPngEngine
        from apps.conversions.engines.pdf_to_xlsx import PdfToXlsxEngine
        from apps.conversions.engines.docx_to_pdf import DocxToPdfEngine
        from apps.conversions.engines.docx_to_image import DocxToJpgEngine, DocxToPngEngine
        from apps.conversions.engines.pptx_to_pdf import PptxToPdfEngine
        from apps.conversions.engines.pptx_to_image import PptxToJpgEngine, PptxToPngEngine
        from apps.conversions.engines.xlsx_to_pdf import XlsxToPdfEngine
        from apps.conversions.engines.xlsx_to_jpg import XlsxToJpgEngine
        from apps.conversions.engines.xlsx_to_png import XlsxToPngEngine
        from apps.conversions.engines.csv_to_xlsx import CsvToXlsxEngine
        from apps.conversions.engines.csv_to_pdf import CsvToPdfEngine
        from apps.conversions.engines.csv_to_jpg import CsvToJpgEngine
        from apps.conversions.engines.csv_to_png import CsvToPngEngine

        engine_registry.register(PdfToDocxEngine)
        engine_registry.register(PdfToJpgEngine)
        engine_registry.register(PdfToPngEngine)
        engine_registry.register(PdfToXlsxEngine)
        engine_registry.register(DocxToPdfEngine)
        engine_registry.register(DocxToJpgEngine)
        engine_registry.register(DocxToPngEngine)
        engine_registry.register(PptxToPdfEngine)
        engine_registry.register(PptxToJpgEngine)
        engine_registry.register(PptxToPngEngine)
        engine_registry.register(XlsxToPdfEngine)
        engine_registry.register(XlsxToJpgEngine)
        engine_registry.register(XlsxToPngEngine)
        engine_registry.register(CsvToXlsxEngine)
        engine_registry.register(CsvToPdfEngine)
        engine_registry.register(CsvToJpgEngine)
        engine_registry.register(CsvToPngEngine)



