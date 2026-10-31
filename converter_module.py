"""
converter_module.py

DocuMind - Document Conversion Module

Features:
1. JPG/JPEG to PNG conversion
2. PNG to JPG/JPEG conversion
3. Multiple images to a single PDF
4. PDF pages to PNG images
5. Image rotation (90, 180, 270 degrees)
6. Image resizing with optional aspect ratio preservation

Dependencies:
    pip install Pillow PyMuPDF

Compatible with:
    - Streamlit UploadedFile objects
    - Python file-like objects
    - BytesIO objects
"""

import io
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image, ImageOps, UnidentifiedImageError


# Supported image formats
SUPPORTED_IMAGE_FORMATS = ("JPEG", "PNG")

# Supported output formats
SUPPORTED_OUTPUT_FORMATS = {
    "JPG": "JPEG",
    "JPEG": "JPEG",
    "PNG": "PNG",
}


def _read_file(file):
    """
    Read uploaded files or compatible file-like objects.

    Returns:
        bytes: File contents.

    Raises:
        ValueError: If the file is empty or invalid.
        TypeError: If the input is not file-like.
    """

    if file is None:
        raise ValueError("No file was provided.")

    if isinstance(file, bytes):
        data = file

    elif isinstance(file, bytearray):
        data = bytes(file)

    elif isinstance(file, str):
        with open(file, "rb") as f:
            data = f.read()

    elif hasattr(file, "read"):
        # Preserve the original file position when possible.
        original_position = None

        try:
            if hasattr(file, "tell"):
                original_position = file.tell()

            if hasattr(file, "seek"):
                file.seek(0)

            data = file.read()

        finally:
            if original_position is not None and hasattr(file, "seek"):
                file.seek(original_position)

    else:
        raise TypeError(
            "Input must be a file path, bytes, or file-like object."
        )

    if not data:
        raise ValueError("The uploaded file is empty.")

    if not isinstance(data, bytes):
        data = bytes(data)

    return data


def _open_image(image_file):
    """
    Open and validate an uploaded image.

    Returns:
        PIL.Image.Image: A loaded image object.
    """

    data = _read_file(image_file)

    try:
        image = Image.open(io.BytesIO(data))
        image.load()

        if image.format not in SUPPORTED_IMAGE_FORMATS:
            raise ValueError(
                "Unsupported image format. Only JPG, JPEG and PNG are supported."
            )

        return ImageOps.exif_transpose(image)

    except UnidentifiedImageError:
        raise ValueError("Invalid or unsupported image file.")

    except OSError as error:
        raise ValueError(f"Unable to open image: {error}")


def convert_image(input_file, output_format):
    """
    Convert an image between JPG, JPEG and PNG formats.

    Args:
        input_file: Uploaded image or file-like object.
        output_format (str): Desired output format ('JPG', 'JPEG', 'PNG').

    Returns:
        BytesIO: Converted image.

    Example:
        converted = convert_image(uploaded_file, "PNG")
    """

    output_format = str(output_format).upper().strip()

    if output_format not in SUPPORTED_OUTPUT_FORMATS:
        raise ValueError(
            "Invalid output format. Choose JPG, JPEG or PNG."
        )

    image = _open_image(input_file)

    target_format = SUPPORTED_OUTPUT_FORMATS[output_format]

    output = io.BytesIO()

    try:
        if target_format == "JPEG":
            # JPEG does not support transparency.
            if image.mode in ("RGBA", "LA") or "transparency" in image.info:
                rgba_image = image.convert("RGBA")
                background = Image.new(
                    "RGB",
                    rgba_image.size,
                    (255, 255, 255)
                )
                background.paste(
                    rgba_image,
                    mask=rgba_image.getchannel("A")
                )
                image = background
            else:
                image = image.convert("RGB")

            image.save(
                output,
                format="JPEG",
                quality=95,
                optimize=True,
                subsampling=0
            )

        else:
            image.save(
                output,
                format="PNG",
                optimize=True
            )

        output.seek(0)
        return output

    except OSError as error:
        raise ValueError(f"Image conversion failed: {error}")


def image_to_pdf(images):
    """
    Combine multiple JPG/PNG images into one PDF document.

    Args:
        images (list): List of uploaded images or file-like objects.

    Returns:
        BytesIO: Generated PDF document.

    Example:
        pdf = image_to_pdf([image1, image2, image3])
    """

    if not images:
        raise ValueError("No images were provided.")

    if not isinstance(images, (list, tuple)):
        images = [images]

    if len(images) == 0:
        raise ValueError("The image list is empty.")

    pil_images = []

    for image_file in images:
        image = _open_image(image_file)

        # Convert to RGB for PDF compatibility.
        if image.mode != "RGB":
            image = image.convert("RGB")

        pil_images.append(image.copy())

    output = io.BytesIO()

    try:
        first_image = pil_images[0]
        remaining_images = pil_images[1:]

        first_image.save(
            output,
            format="PDF",
            save_all=True,
            append_images=remaining_images,
            resolution=150.0,
            quality=95
        )

        output.seek(0)
        return output

    except OSError as error:
        raise ValueError(f"Image to PDF conversion failed: {error}")

    finally:
        for image in pil_images:
            image.close()


def pdf_to_images(pdf_file):
    """
    Convert every page of a PDF into a PNG image.

    Args:
        pdf_file: Uploaded PDF or compatible file-like object.

    Returns:
        list: List of BytesIO objects containing PNG images.

    Example:
        pages = pdf_to_images(uploaded_pdf)

        for index, page in enumerate(pages):
            page.seek(0)
    """

    pdf_data = _read_file(pdf_file)

    if not pdf_data.startswith(b"%PDF"):
        raise ValueError("Invalid PDF file.")

    images = []

    try:
        document = fitz.open(
            stream=pdf_data,
            filetype="pdf"
        )

        if document.page_count == 0:
            raise ValueError("The PDF contains no pages.")

        try:
            for page in document:
                # Render page at 2x resolution for good image quality.
                pixmap = page.get_pixmap(
                    matrix=fitz.Matrix(2, 2),
                    colorspace=fitz.csRGB,
                    alpha=False
                )

                png_data = pixmap.tobytes("png")

                image_buffer = io.BytesIO(png_data)
                image_buffer.seek(0)

                images.append(image_buffer)

        finally:
            document.close()

        return images

    except fitz.FileDataError:
        raise ValueError("The PDF file is corrupted or invalid.")

    except Exception as error:
        if isinstance(error, ValueError):
            raise

        raise ValueError(f"PDF to image conversion failed: {error}")


def rotate_image(image_file, angle):
    """
    Rotate an image by 90, 180 or 270 degrees.

    Args:
        image_file: Uploaded image or file-like object.
        angle (int): Rotation angle (90, 180 or 270).

    Returns:
        BytesIO: Rotated PNG image.

    Example:
        rotated = rotate_image(uploaded_file, 90)
    """

    if angle not in (90, 180, 270):
        raise ValueError(
            "Invalid rotation angle. Choose 90, 180 or 270 degrees."
        )

    image = _open_image(image_file)

    try:
        # PIL rotates counterclockwise.
        rotated = image.rotate(
            angle,
            expand=True
        )

        output = io.BytesIO()

        if rotated.mode not in ("RGB", "RGBA"):
            rotated = rotated.convert("RGBA")

        rotated.save(
            output,
            format="PNG",
            optimize=True
        )

        output.seek(0)

        return output

    except OSError as error:
        raise ValueError(f"Image rotation failed: {error}")


def resize_image(image_file, width, height, preserve_aspect_ratio=True):
    """
    Resize an image to the requested dimensions.

    Args:
        image_file: Uploaded image or file-like object.
        width (int): Target width in pixels.
        height (int): Target height in pixels.
        preserve_aspect_ratio (bool): Preserve original aspect ratio.

    Returns:
        BytesIO: Resized PNG image.

    Example:
        resized = resize_image(
            uploaded_file,
            800,
            600,
            preserve_aspect_ratio=True
        )
    """

    if not isinstance(width, int) or not isinstance(height, int):
        raise TypeError("Width and height must be integers.")

    if width <= 0 or height <= 0:
        raise ValueError("Width and height must be positive.")

    image = _open_image(image_file)

    try:
        if preserve_aspect_ratio:
            resized = ImageOps.contain(
                image,
                (width, height),
                method=Image.Resampling.LANCZOS
            )
        else:
            resized = image.resize(
                (width, height),
                Image.Resampling.LANCZOS
            )

        output = io.BytesIO()

        if resized.mode not in ("RGB", "RGBA"):
            resized = resized.convert("RGBA")

        resized.save(
            output,
            format="PNG",
            optimize=True
        )

        output.seek(0)

        return output

    except OSError as error:
        raise ValueError(f"Image resizing failed: {error}")


# Module test
if __name__ == "__main__":
    print("DocuMind Converter Module")
    print("-------------------------")
    print("Available functions:")
    print("1. convert_image(input_file, output_format)")
    print("2. image_to_pdf(images)")
    print("3. pdf_to_images(pdf_file)")
    print("4. rotate_image(image_file, angle)")
    print(
        "5. resize_image(image_file, width, height, "
        "preserve_aspect_ratio=True)"
    )
    print("\nModule loaded successfully.")