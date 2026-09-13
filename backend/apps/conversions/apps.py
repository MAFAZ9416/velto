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

        from apps.conversions.engines.image_engine import (
            JpgToPngEngine,
            PngToJpgEngine,
            ImagesToZipEngine,
            make_generic_image_engine_class,
        )

        from apps.conversions.engines.document_engine import (
            TxtToPdfEngine,
            TxtToDocxEngine,
            HtmlToPdfEngine,
            HtmlToDocxEngine,
            MarkdownToPdfEngine,
            MarkdownToDocxEngine,
        )

        from apps.conversions.engines.pdf_utility_engine import (
            PdfMergeEngine,
            PdfSplitEngine,
            PdfExtractPagesEngine,
            PdfRotateEngine,
            PdfCompressEngine,
            PdfWatermarkEngine,
            PdfProtectEngine,
            PdfUnlockEngine,
            PdfMetadataEngine,
            PdfPageNumbersEngine,
            PdfRepairEngine,
        )

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

        # Register Document engines
        engine_registry.register(TxtToPdfEngine)
        engine_registry.register(TxtToDocxEngine)
        engine_registry.register(HtmlToPdfEngine)
        engine_registry.register(HtmlToDocxEngine)
        engine_registry.register(MarkdownToPdfEngine)
        engine_registry.register(MarkdownToDocxEngine)

        # Register PDF Utility engines
        engine_registry.register(PdfMergeEngine)
        engine_registry.register(PdfSplitEngine)
        engine_registry.register(PdfExtractPagesEngine)
        engine_registry.register(PdfRotateEngine)
        engine_registry.register(PdfCompressEngine)
        engine_registry.register(PdfWatermarkEngine)
        engine_registry.register(PdfProtectEngine)
        engine_registry.register(PdfUnlockEngine)
        engine_registry.register(PdfMetadataEngine)
        engine_registry.register(PdfPageNumbersEngine)
        engine_registry.register(PdfRepairEngine)

        # Register Image engines
        engine_registry.register(JpgToPngEngine)
        engine_registry.register(PngToJpgEngine)
        engine_registry.register(ImagesToZipEngine)

        # Register remaining generic image conversion pairs
        image_formats = {"jpg", "png", "webp", "bmp", "tiff", "gif"}
        for src in image_formats:
            for tgt in image_formats:
                if (src, tgt) in [("jpg", "png"), ("png", "jpg")]:
                    continue  # already registered above
                if engine_registry.get(src, tgt) is None:
                    cls = make_generic_image_engine_class(src, tgt)
                    engine_registry.register(cls)

            # Also register image -> zip engine for individual format keys
            if engine_registry.get(src, "zip") is None:
                zip_cls = make_generic_image_engine_class(src, "zip")
                # Use ImagesToZipEngine convert method
                zip_cls.convert = lambda self, input_path, output_path, options=None: ImagesToZipEngine().convert(input_path, output_path, options)
                engine_registry.register(zip_cls)




