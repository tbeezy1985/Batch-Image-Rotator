from pathlib import Path
from uuid import uuid4
import os
import shutil

from flask import Flask, redirect, render_template, request, send_file, url_for
from werkzeug.utils import secure_filename

from rotate_images_to_zip import rotate_images


BASE_DIR = Path(__file__).resolve().parent
RUNS_DIR = BASE_DIR / "tree_rotator_runs"
ALLOWED_EXTENSIONS = {".zip"}


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024 * 1024


def parse_angles(form):
    angles = []

    for raw_angle in form.getlist("angles"):
        angles.append(float(raw_angle))

    custom_angles = form.get("custom_angles", "")
    for raw_angle in custom_angles.replace(",", " ").split():
        angles.append(float(raw_angle))

    unique_angles = []
    for angle in angles:
        if angle not in unique_angles:
            unique_angles.append(angle)

    if not unique_angles:
        raise ValueError("Choose at least one rotation angle.")

    return unique_angles


def class_summary(output_folder):
    folder = Path(output_folder)
    rows = []

    for child in sorted(folder.iterdir(), key=lambda path: path.name.lower()):
        if child.is_dir():
            rows.append(
                {
                    "name": child.name.strip(),
                    "count": sum(1 for file_path in child.rglob("*") if file_path.is_file()),
                }
            )

    return rows


def save_uploads(files, upload_dir):
    input_paths = []
    upload_dir.mkdir(parents=True, exist_ok=True)

    for file_storage in files:
        if not file_storage or not file_storage.filename:
            continue

        filename = secure_filename(file_storage.filename)
        if not filename:
            continue

        if Path(filename).suffix.lower() not in ALLOWED_EXTENSIONS:
            raise ValueError("Please upload .zip files only.")

        destination = upload_dir / filename
        file_storage.save(destination)
        input_paths.append(destination)

    if not input_paths:
        raise ValueError("Upload at least one zip file.")

    return input_paths


@app.get("/")
def index():
    return render_template("tree_rotator.html")


@app.post("/rotate")
def rotate():
    run_id = uuid4().hex
    run_dir = RUNS_DIR / run_id
    upload_dir = run_dir / "uploads"
    output_folder = run_dir / "rotated_tree_images"
    zip_file = run_dir / "rotated_tree_images.zip"

    try:
        input_paths = save_uploads(request.files.getlist("image_zips"), upload_dir)
        angles = parse_angles(request.form)

        result = rotate_images(
            input_paths=input_paths,
            output_folder=output_folder,
            zip_file=zip_file,
            angles=angles,
            save_originals=request.form.get("save_originals") == "on",
            keep_subfolders=request.form.get("keep_subfolders") == "on",
        )

        return render_template(
            "tree_rotator.html",
            result=result,
            run_id=run_id,
            angles=angles,
            classes=class_summary(output_folder),
        )
    except Exception as error:
        if run_dir.exists():
            shutil.rmtree(run_dir)
        return render_template("tree_rotator.html", error=str(error)), 400


@app.get("/download/<run_id>")
def download(run_id):
    zip_file = RUNS_DIR / secure_filename(run_id) / "rotated_tree_images.zip"
    if not zip_file.exists():
        return redirect(url_for("index"))

    return send_file(zip_file, as_attachment=True, download_name="rotated_tree_images.zip")


if __name__ == "__main__":
    RUNS_DIR.mkdir(exist_ok=True)
    port = int(os.environ.get("PORT", "5050"))
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG") == "1")
