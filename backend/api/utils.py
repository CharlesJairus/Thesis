import qrcode
import qrcode.constants
import cv2
from io import BytesIO
from django.core.files import File
import numpy as np
from ultralytics import YOLO
import os
from django.core.mail import EmailMessage
from django.conf import settings
from .models import Student, StudentLogs
from django.utils import timezone



def generate_and_save_qr_to_model(data, instance,student):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    email = EmailMessage(
        subject='Uniform Scanner Result',
        body=f'An Account has been created for you with the following details:\n\n'
             f'name: {student.firstName} {student.middleInitial}. {student.lastName}\n'
             f'Email: {student.email}\n\n'
             f'Please use the QR code attached to this email for your attendance.',
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=['faceless7078@gmail.com',student.email],
    )
    email.attach('qr_code.png', buffer.read(), 'image/png')

    email.send()
    buffer.seek(0)
    instance.qr_code.save(f"{data}.png", File(buffer), save=False)
    
    
def qr_scanner(img_file):
    # Convert Django's InMemoryUploadedFile to a format OpenCV can read
    img_array = np.frombuffer(img_file.read(), np.uint8)
    image = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    
    if image is None:
        return None
    
    qr_det = cv2.QRCodeDetector()
    decoded, _, _ = qr_det.detectAndDecode(image)
    
    return decoded

def uniform_scanner(img_file,student):
    img_file.seek(0)
    img_array = np.frombuffer(img_file.read(), np.uint8)
    frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

    if frame is None:
        print("Failed to load image.")
        return None

    
    model_path = os.path.join(os.path.dirname(__file__), "UniformDetectionModelV3.pt")
    model = YOLO(model_path)

    
    results = model(frame)[0]

    print(results)
    detected_objects = []
    
    for box in results.boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        conf = float(box.conf[0])
        cls = int(box.cls[0])
        label = f'{model.names[cls]} {conf:.2f}'
        
        detected_objects.append({
            "bbox": [x1, y1, x2, y2],
            "confidence": conf,
            "class_id": cls,
            "label": label,
        })

        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(frame, label, (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
    if detected_objects:
        
        cls = detected_objects[-1]['class_id']
        class_name = model.names[cls]

        if class_name == "CompleteUniform":
            StudentLogs.objects.create(
                student=student, 
                log_type='CU',
                timestamp=timezone.now()
            )
        else:
            StudentLogs.objects.create(
                student=student, 
                log_type='IU',
                timestamp=timezone.now()
            )
        
    else:
        uniform_status = "No Uniform Detected"
        StudentLogs.objects.create(
                student=student, 
                log_type='IU',
                timestamp=timezone.now()
            )
        
    _, jpeg = cv2.imencode('.jpg', frame)
    jpeg_bytes = jpeg.tobytes()
    buffer = BytesIO(jpeg_bytes)
    buffer.seek(0)
    
    uniform_status = "Uniform Detected" if detected_objects else "No Uniform Detected"

    
    if detected_objects:
        object_summary = "\n".join([f"- {obj['label']} at {obj['bbox']}" for obj in detected_objects])
    else:
        object_summary = "No uniform-related objects were detected in the scan."

    # Compose the email
    email = EmailMessage(
        subject='[Uniform Scanner] Detection Summary',
        body=(
            f"Dear {student.fullName},\n\n"
            f"This is to inform you that your recent scan has been processed.\n\n"
            f"Detection Result: {uniform_status}\n\n"
            f"Details:\n{object_summary}\n\n"
            f"If this detection appears incorrect, please contact your supervisor.\n\n"
            f"Regards,\nUniform Monitoring System"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=['faceless7078@gmail.com', student.email],
    )

    # Attach the image of the detection result
    email.attach('detected.jpg', buffer.read(), 'image/jpeg')
    email.send()

    return frame, detected_objects 

    