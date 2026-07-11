import cv2
import torch
import clip
import numpy as np
import pyautogui
import pytesseract
from PIL import Image
import time
from datetime import datetime
import os
from collections import Counter

# =========================================================
# EMAIL IMPORTS
# =========================================================
import smtplib

from email.mime.text import MIMEText

from email.mime.multipart import MIMEMultipart

from email.mime.image import MIMEImage

# =========================================================
# TESSERACT OCR PATH
# =========================================================
pytesseract.pytesseract.tesseract_cmd = (
    r'C:\Program Files\Tesseract-OCR\tesseract.exe'
)

# =========================================================
# CREATE ALERT FOLDER
# =========================================================
if not os.path.exists("alerts"):
    os.makedirs("alerts")

# =========================================================
# DEVICE
# =========================================================
device = "cuda" if torch.cuda.is_available() else "cpu"

print("=" * 70)
print("AI CYBERSECURITY VISION MONITOR")
print("=" * 70)
print(f"[INFO] Running on device: {device}")

# =========================================================
# LOAD CLIP MODEL
# =========================================================
model, preprocess = clip.load("ViT-B/32", device=device)

print("[INFO] CLIP model loaded successfully")

# =========================================================
# EMAIL CONFIG
# =========================================================
# Read from environment variables (.env file)
# =========================================================
from dotenv import load_model, load_dotenv
load_dotenv()

EMAIL_CONFIG = {
    "sender": os.getenv("EMAIL_SENDER", "gongolf444@gmail.com"),
    "app_password": os.getenv("EMAIL_APP_PASSWORD", ""),
    "receiver": os.getenv("EMAIL_RECEIVER", "gongolf444@gmail.com"),
    "smtp_host": os.getenv("EMAIL_SMTP_HOST", "smtp.gmail.com"),
    "smtp_port": int(os.getenv("EMAIL_SMTP_PORT", 587))
}

# =========================================================
# PROMPTS
# =========================================================
prompts = [

    # =====================================================
    # NORMAL ENVIRONMENT
    # =====================================================

    "a normal Windows desktop screen",

    "a Microsoft Word document on screen",

    "a normal office computer environment",

    "a web browser showing normal websites",

    "a software development environment with VS Code",

    "a person using a normal business computer",

    # =====================================================
    # TERMINAL / COMMAND LINE
    # =====================================================

    "a Windows command prompt terminal window",

    "a PowerShell terminal with command line interface",

    "a Linux terminal window with command execution",

    # =====================================================
    # CYBERSECURITY TOOLS
    # =====================================================

    "a cybersecurity monitoring dashboard",

    "a network traffic analysis tool",

    "a Wireshark packet analysis interface",

    "a penetration testing environment on computer screen",

    "a Kali Linux desktop with security tools",

    "a Metasploit terminal used for penetration testing",

    # =====================================================
    # MALICIOUS / ATTACK
    # =====================================================

    "a phishing login webpage pretending to be a bank",

    "a suspicious fake login website",

    "a ransomware warning message on computer",

    "a malware attack notification screen",

    "a suspicious hacking activity on a computer screen"
]

# =========================================================
# TOKENIZE PROMPTS
# =========================================================
text = clip.tokenize(prompts).to(device)

# =========================================================
# RISK MAP
# =========================================================
risk_map = {

    # NORMAL
    "a normal Windows desktop screen": 0,
    "a Microsoft Word document on screen": 0,
    "a normal office computer environment": 0,
    "a web browser showing normal websites": 5,
    "a software development environment with VS Code": 10,
    "a person using a normal business computer": 5,

    # TERMINAL
    "a Windows command prompt terminal window": 20,
    "a PowerShell terminal with command line interface": 30,
    "a Linux terminal window with command execution": 40,

    # CYBERSECURITY
    "a cybersecurity monitoring dashboard": 35,
    "a network traffic analysis tool": 45,
    "a Wireshark packet analysis interface": 55,
    "a penetration testing environment on computer screen": 70,
    "a Kali Linux desktop with security tools": 80,
    "a Metasploit terminal used for penetration testing": 90,

    # MALICIOUS
    "a phishing login webpage pretending to be a bank": 95,
    "a suspicious fake login website": 90,
    "a ransomware warning message on computer": 100,
    "a malware attack notification screen": 95,
    "a suspicious hacking activity on a computer screen": 85
}

# =========================================================
# OCR CYBERSECURITY KEYWORDS
# =========================================================
dangerous_keywords = {

    "sudo": 20,
    "nmap": 40,
    "password": 30,
    "token": 20,
    "api_key": 30,
    "apikey": 30,
    "metasploit": 50,
    "payload": 40,
    "wireshark": 30,
    "hashcat": 60,
    "hydra": 60,
    "sqlmap": 70,
    "rm -rf": 100,
    "exploit": 50,
    "malware": 70,
    "powershell": 25,
    "credential": 40,
    "backdoor": 80
}

# =========================================================
# SETTINGS
# =========================================================
CONFIDENCE_THRESHOLD = 35

ALERT_THRESHOLD = 80

COOLDOWN_SECONDS = 10

# =========================================================
# TEMPORAL STABILITY FILTER
# =========================================================
prediction_history = []

# =========================================================
# ALERT CONTROL
# =========================================================
last_alert_time = 0

# =========================================================
# SEND EMAIL ALERT FUNCTION
# =========================================================
def send_email_alert(
    threat_level,
    risk_score,
    detected_label,
    image_path,
    detected_keywords
):

    try:

        # =================================================
        # EMAIL SUBJECT
        # =================================================
        subject = (
            f"[ALERT] {threat_level} Threat Detected"
        )

        # =================================================
        # EMAIL BODY
        # =================================================
        body = f"""
AI Cybersecurity Vision Monitor Alert

Threat Level : {threat_level}

Risk Score   : {risk_score}

Detected Context:
{detected_label}

Detected Keywords:
{', '.join(detected_keywords) if detected_keywords else 'None'}

Timestamp:
{datetime.now()}

Please investigate immediately.
"""

        # =================================================
        # CREATE EMAIL MESSAGE
        # =================================================
        msg = MIMEMultipart()

        msg["From"] = EMAIL_CONFIG["sender"]

        msg["To"] = EMAIL_CONFIG["receiver"]

        msg["Subject"] = subject

        msg.attach(
            MIMEText(body, "plain")
        )

        # =================================================
        # ATTACH SCREENSHOT IMAGE
        # =================================================
        with open(image_path, "rb") as img_file:

            img = MIMEImage(img_file.read())

            img.add_header(
                "Content-Disposition",
                f'attachment; filename="{os.path.basename(image_path)}"'
            )

            msg.attach(img)

        # =================================================
        # SMTP CONNECTION
        # =================================================
        server = smtplib.SMTP(
            EMAIL_CONFIG["smtp_host"],
            EMAIL_CONFIG["smtp_port"]
        )

        server.starttls()

        server.login(
            EMAIL_CONFIG["sender"],
            EMAIL_CONFIG["app_password"]
        )

        server.send_message(msg)

        server.quit()

        print("\n📧 Email Alert Sent Successfully")

    except Exception as e:

        print("\n❌ Failed to Send Email")

        print(e)

# =========================================================
# MAIN LOOP
# =========================================================
while True:

    # =====================================================
    # SCREEN CAPTURE
    # =====================================================
    screenshot = pyautogui.screenshot()

    frame = cv2.cvtColor(
        np.array(screenshot),
        cv2.COLOR_RGB2BGR
    )

    # =====================================================
    # PREPARE IMAGE FOR CLIP
    # =====================================================
    pil_image = Image.fromarray(
        cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    )

    image_input = preprocess(
        pil_image
    ).unsqueeze(0).to(device)

    # =====================================================
    # CLIP INFERENCE
    # =====================================================
    with torch.no_grad():

        logits_per_image, logits_per_text = model(
            image_input,
            text
        )

        probs = (
            logits_per_image
            .softmax(dim=-1)
            .cpu()
            .numpy()[0]
        )

    # =====================================================
    # TOP PREDICTIONS
    # =====================================================
    top_indices = probs.argsort()[-3:][::-1]

    best_idx = top_indices[0]

    detected_label = prompts[best_idx]

    confidence = probs[best_idx] * 100

    # =====================================================
    # STABILITY FILTER
    # =====================================================
    prediction_history.append(detected_label)

    if len(prediction_history) > 5:
        prediction_history.pop(0)

    stable_prediction = (
        Counter(prediction_history)
        .most_common(1)[0][0]
    )

    # =====================================================
    # OCR TEXT EXTRACTION
    # =====================================================
    ocr_text = pytesseract.image_to_string(frame)

    # =====================================================
    # INITIAL RISK SCORE
    # =====================================================
    risk_score = risk_map[stable_prediction]

    # ===================================================== 
    # OCR KEYWORD ANALYSIS
    # =====================================================
    detected_keywords = []

    for keyword, score in dangerous_keywords.items():

        if keyword.lower() in ocr_text.lower():

            risk_score += score

            detected_keywords.append(keyword)

    # =====================================================
    # LIMIT MAX SCORE
    # =====================================================
    risk_score = min(risk_score, 100)

    # =====================================================
    # LOW CONFIDENCE HANDLING
    # =====================================================
    if confidence < CONFIDENCE_THRESHOLD:

        threat_level = "UNCERTAIN"

        color = (180, 180, 180)

    else:

        if risk_score >= 90:

            threat_level = "CRITICAL"

            color = (0, 0, 255)

        elif risk_score >= 70:

            threat_level = "HIGH"

            color = (0, 100, 255)

        elif risk_score >= 40:

            threat_level = "MEDIUM"

            color = (0, 255, 255)

        else:

            threat_level = "LOW"

            color = (0, 255, 0)

    # =====================================================
    # CLEAR TERMINAL
    # =====================================================
    os.system("cls")

    # =====================================================
    # TERMINAL OUTPUT
    # =====================================================
    print("=" * 70)

    print(f"Detected Context : {stable_prediction}")

    print(f"Confidence       : {confidence:.2f}%")

    print(f"Risk Score       : {risk_score}")

    print(f"Threat Level     : {threat_level}")

    print("\nTop Predictions:")

    for idx in top_indices:

        print(
            f"  - {prompts[idx]} : "
            f"{probs[idx]*100:.2f}%"
        )

    # =====================================================
    # OCR KEYWORDS
    # =====================================================
    if detected_keywords:

        print("\nDetected Keywords:")

        for keyword in detected_keywords:

            print(f"  - {keyword}")

    else:

        print("\nDetected Keywords: None")

    print("=" * 70)

    # =====================================================
    # ALERT SYSTEM
    # =====================================================
    current_time = time.time()

    if (
        confidence > CONFIDENCE_THRESHOLD
        and risk_score >= ALERT_THRESHOLD
        and current_time - last_alert_time > COOLDOWN_SECONDS
    ):

        print("\n⚠ SECURITY ALERT DETECTED")

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        filename = f"alerts/alert_{timestamp}.jpg"

        # =================================================
        # SAVE SCREENSHOT
        # =================================================
        cv2.imwrite(filename, frame)

        print(f"📸 Evidence Saved: {filename}")

        # =================================================
        # SEND EMAIL ALERT
        # =================================================
        send_email_alert(
            threat_level,
            risk_score,
            stable_prediction,
            filename,
            detected_keywords
        )

        last_alert_time = current_time

    # =====================================================
    # DISPLAY TEXT ON SCREEN
    # =====================================================
    cv2.putText(
        frame,
        f"{threat_level} | Risk: {risk_score}",
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        color,
        3
    )

    cv2.putText(
        frame,
        stable_prediction,
        (20, 80),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        color,
        2
    )

    # =====================================================
    # DISPLAY WINDOW
    # =====================================================
    cv2.imshow(
        "AI Cybersecurity Vision Monitor",
        frame
    )

    # =====================================================
    # EXIT PROGRAM
    # =====================================================
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

    time.sleep(2)

# =========================================================
# CLEANUP
# =========================================================
cv2.destroyAllWindows()