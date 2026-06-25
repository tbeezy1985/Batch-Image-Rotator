from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile
import argparse
import shutil

from PIL import Image, ImageOps


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}
MAX_IMAGE_SIDE = 1200
SAVE_QUALITY = 88


def safe_angle_name(angle):
    return str(angle).replace("-", "neg").replace(".", "p")


def output_path_for(input_file, input_root, output_root, suffix, keep_subfolders):
    if keep_subfolders:
        relative_parent = input_file.parent.relative_to(input_root)
        output_dir = output_root / relative_parent
    else:
        output_dir = output_root

    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / f"{input_file.stem}_{suffix}{input_file.suffix.lower()}"


def rotate_image(image, angle):
    return image.rotate(angle, expand=True, fillcolor=(255, 255, 255))


def prepare_image_for_training(image):
    image.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE), Image.Resampling.LANCZOS)
    return image


def zip_folder(folder, zip_path):
    with ZipFile(zip_path, "w", ZIP_DEFLATED) as zip_file:
        for file_path in folder.rglob("*"):
            if file_path.is_file():
                zip_file.write(file_path, file_path.relative_to(folder))


def unzip_input(zip_path, unzip_folder):
    with ZipFile(zip_path, "r") as zip_file:
        zip_file.extractall(unzip_folder)

    return Path(unzip_folder)


def prepare_inputs(input_paths, temp_dir):
    combined_root = Path(temp_dir) / "combined_input"
    combined_root.mkdir()

    for input_path in input_paths:
        input_path = Path(input_path).expanduser().resolve()

        if not input_path.exists():
            raise FileNotFoundError(f"Input does not exist: {input_path}")

        if input_path.is_file() and input_path.suffix.lower() == ".zip":
            unzip_input(input_path, combined_root)
        elif input_path.is_dir():
            destination = combined_root / input_path.name
            shutil.copytree(input_path, destination)
        else:
            raise ValueError("Each input must be a folder or a .zip file.")

    return combined_root


def rotate_images(
    input_paths,
    output_folder,
    zip_file,
    angles,
    save_originals=True,
    keep_subfolders=True,
):
    output_root = Path(output_folder).expanduser().resolve()
    zip_path = Path(zip_file).expanduser().resolve()

    with TemporaryDirectory() as temp_dir:
        input_root = prepare_inputs(input_paths, temp_dir)

        if output_root.exists():
            shutil.rmtree(output_root)
        output_root.mkdir(parents=True)

        image_files = [
            path
            for path in input_root.rglob("*")
            if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
        ]

        if not image_files:
            print("No image files found.")
            return {
                "image_count": 0,
                "saved_count": 0,
                "output_folder": str(output_root),
                "zip_file": str(zip_path),
                "skipped": [],
            }

        saved_count = 0
        skipped = []

        for image_file in image_files:
            try:
                with Image.open(image_file) as image:
                    image = ImageOps.exif_transpose(image).convert("RGB")
                    image = prepare_image_for_training(image)

                    if save_originals:
                        original_output = output_path_for(
                            image_file, input_root, output_root, "original", keep_subfolders
                        )
                        image.save(original_output, quality=SAVE_QUALITY, optimize=True)
                        saved_count += 1

                    for angle in angles:
                        rotated = rotate_image(image, angle)
                        angle_output = output_path_for(
                            image_file,
                            input_root,
                            output_root,
                            f"rot{safe_angle_name(angle)}",
                            keep_subfolders,
                        )
                        rotated.save(angle_output, quality=SAVE_QUALITY, optimize=True)
                        saved_count += 1

            except Exception as error:
                message = f"Skipped {image_file}: {error}"
                skipped.append(message)
                print(message)

        zip_path.parent.mkdir(parents=True, exist_ok=True)
        if zip_path.exists():
            zip_path.unlink()
        zip_folder(output_root, zip_path)

        print(f"Done. Found {len(image_files)} images and saved {saved_count} files.")
        print(f"Rotated image folder: {output_root}")
        print(f"Zip file: {zip_path}")
        return {
            "image_count": len(image_files),
            "saved_count": saved_count,
            "output_folder": str(output_root),
            "zip_file": str(zip_path),
            "skipped": skipped,
        }


def main():
    parser = argparse.ArgumentParser(
        description="Rotate local image folders or zip files and save the result as a zip file."
    )
    parser.add_argument(
        "input_paths",
        nargs="+",
        help="One or more folders or .zip files containing original images.",
    )
    parser.add_argument(
        "--output-folder",
        default="rotated_tree_images",
        help="Folder where rotated images will be saved.",
    )
    parser.add_argument(
        "--zip-file",
        default="rotated_tree_images.zip",
        help="Name of the zip file to create.",
    )
    parser.add_argument(
        "--angles",
        nargs="+",
        type=float,
        default=[90, 180, 270],
        help="Rotation angles to create, such as --angles -15 -10 10 15 90 180 270",
    )
    parser.add_argument(
        "--no-originals",
        action="store_true",
        help="Only save rotated images, not copies of the originals.",
    )
    parser.add_argument(
        "--flat",
        action="store_true",
        help="Put all images in one output folder instead of keeping subfolders.",
    )

    args = parser.parse_args()

    rotate_images(
        input_paths=args.input_paths,
        output_folder=args.output_folder,
        zip_file=args.zip_file,
        angles=args.angles,
        save_originals=not args.no_originals,
        keep_subfolders=not args.flat,
    )


if __name__ == "__main__":
    main()
