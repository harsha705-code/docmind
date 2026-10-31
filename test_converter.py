from converter_module import (
    convert_image,
    image_to_pdf,
    pdf_to_images,
    rotate_image,
    resize_image
)

# 1. JPG to PNG
with open("sample.jpg", "rb") as f:
    result = convert_image(f, "PNG")

with open("converted.png", "wb") as f:
    f.write(result.getvalue())

print("1. JPG to PNG: SUCCESS")


# 2. Multiple images to PDF
with open("sample.jpg", "rb") as f1, open("sample.png", "rb") as f2:
    result = image_to_pdf([f1, f2])

with open("combined.pdf", "wb") as f:
    f.write(result.getvalue())

print("2. Images to PDF: SUCCESS")


# 3. PDF to images
with open("sample.pdf", "rb") as f:
    pages = pdf_to_images(f)

for i, page in enumerate(pages):
    with open(f"page_{i+1}.png", "wb") as output:
        output.write(page.getvalue())

print("3. PDF to Images: SUCCESS")


# 4. Rotate image
with open("sample.jpg", "rb") as f:
    result = rotate_image(f, 90)

with open("rotated.png", "wb") as output:
    output.write(result.getvalue())

print("4. Image Rotation: SUCCESS")


# 5. Resize image
with open("sample.jpg", "rb") as f:
    result = resize_image(f, 800, 600)

with open("resized.png", "wb") as output:
    output.write(result.getvalue())

print("5. Image Resizing: SUCCESS")


print("\nALL CONVERTER TESTS COMPLETED!")