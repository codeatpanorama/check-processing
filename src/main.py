import os
from google.cloud import storage
from flask import Flask, request, jsonify

# Flask app is used by the functions framework
app = Flask(__name__)

# Configure Google Cloud Storage client
storage_client = storage.Client()

# Name of the bucket (set this as an environment variable)
BUCKET_NAME = os.environ.get("BUCKET_NAME", "m2-solutions")

@app.route("/", methods=["POST"])
def upload_to_bucket(request):
    """
    HTTP Cloud Function to upload a binary file to Google Cloud Storage.
    """
    # Check if a file is in the request
    if 'file' not in request.files:
        return jsonify({"error": "No file provided in the request"}), 400

    file = request.files['file']

    # Validate file
    if file.filename == '':
        return jsonify({"error": "File name is empty"}), 400

    try:
        # Define destination blob name (same as uploaded filename)
        destination_blob_name = file.filename

        # Access the bucket
        bucket = storage_client.bucket(BUCKET_NAME)

        # Create a new blob and upload file content
        blob = bucket.blob(destination_blob_name)
        blob.upload_from_file(file, content_type=file.content_type)

        # Make the file publicly accessible (optional)
        # blob.make_public()

        # Return the public URL of the file
        return jsonify({
            "message": "File uploaded successfully",
            "file_name": destination_blob_name,
            "bucket": BUCKET_NAME,
            "file_url": f"https://storage.googleapis.com/{BUCKET_NAME}/{destination_blob_name}"
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


import os
import json
from google.cloud import storage
from google.cloud import vision
from google.cloud import firestore
from flask import Request


# Initialize Google Cloud clients
storage_client = storage.Client()
vision_client = vision.ImageAnnotatorClient()
firestore_client = firestore.Client()

def process_file(event, context=None):
    """
    Cloud Function triggered by a Cloud Storage event.
    Processes the uploaded file with Vision API and logs extracted text to Firestore.

    Args:
        event (dict): The Cloud Storage event payload.
        context (google.cloud.functions.Context): Metadata for the event.
    """

    # Ensure the function works locally without a 'context' argument
    # Parse JSON payload when running locally
    if isinstance(request, Request):
        event = request.get_json(silent=True)
        if not event:
            raise ValueError("Invalid or missing JSON payload in request.")
    else:
        # In production, `event` will already be a dictionary
        event = request

    bucket_name = event['bucket']  # Bucket where the file was uploaded
    file_name = event['name']  # File name in the bucket
    content_type = event['contentType']  # File's content type

    print(f"Processing file: {file_name} from bucket: {bucket_name} of type: {content_type}")

    # Only process image files
    if not content_type.startswith('image/'):
        print(f"Skipping non-image file: {file_name}")
        return

    try:
        # Download the file from GCS to memory
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(file_name)
        image_content = blob.download_as_bytes()

        # Perform text detection using Vision API
        image = vision.Image(content=image_content)
        response = vision_client.text_detection(image=image)

        if response.error.message:
            raise Exception(f"Vision API error: {response.error.message}")

        # Extract text from the Vision API response
        extracted_text = response.text_annotations[0].description if response.text_annotations else ""
        print(f"Extracted text: {extracted_text}")

        # Store the extracted text in Firestore
        #doc_ref = firestore_client.collection("processed_checks").document(file_name)
        # doc_ref.set({
        #     "file_name": file_name,
        #     "bucket": bucket_name,
        #     "extracted_text": extracted_text,
        #     "content_type": content_type
        # })

        print(f"Stored extracted text for file: {file_name} in Firestore")

    except Exception as e:
        print(f"Error processing file {file_name}: {str(e)}")
        raise

