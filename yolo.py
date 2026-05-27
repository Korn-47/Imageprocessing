import cv2
import numpy as np
import pyautogui
import pytesseract
from ultralytics import YOLO
import time
import logging
import smtplib
from email.mime.text import MIMEText
from datetime import datetime
import json
import os
import sys

# --- 1. INITIAL SETUP ---
def load_config():
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ [CRITICAL] Cannot load config.json: {e}")
        sys.exit(1)

CONFIG = load_config()
# ดึง Path Tesseract จาก Config (ถ้ามี) หรือใช้ Default
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

for folder in ['logs', 'alerts']:
    if not os.path.exists(folder):
        os.makedirs(folder)

class AVSAS_Auditor:
    def __init__(self):
        # ดึงค่าตามโครงสร้าง JSON ของคุณก้อนเป๊ะๆ
        self.email_cfg = CONFIG.get("email", {})
        self.monitor_cfg = CONFIG.get("monitor", {})
        self.policies = CONFIG.get("security_policies", {})
        
        self.model = YOLO(self.monitor_cfg.get("model_path", "yolov8n.pt"))
        self.interval = self.monitor_cfg.get("audit_interval", 3)
        self.cooldown = self.monitor_cfg.get("alert_cooldown_seconds", 60)
        self.yolo_conf = self.monitor_cfg.get("yolo_confidence", 0.4)
        
        self.alert_history = {} 
        self.session_stats = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        self.start_time = datetime.now()
        self._setup_logging()

    def _setup_logging(self):
        log_name = f"logs/avsas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        logging.basicConfig(
            filename=log_name,
            level=logging.INFO,
            format='%(asctime)s | %(levelname)s | %(message)s'
        )
        self.log_file = log_name

    def _send_email(self, level, pattern, context):
        """ระบบแจ้งเตือนผ่าน Email ตาม Config ของคุณ"""
        sender = self.email_cfg.get("sender")
        receiver = self.email_cfg.get("receiver")
        app_pass = self.email_cfg.get("app_password")
        host = self.email_cfg.get("smtp_host", "smtp.gmail.com")
        port = self.email_cfg.get("smtp_port", 465)

        # ตรวจสอบความพร้อมของข้อมูลอีเมล
        if not all([sender, receiver, app_pass]):
            logging.error("Email configuration incomplete. Skipping alert.")
            return

        subject = f"⚠️ [SECURITY ALERT] {level} Risk Detected"
        body = f"Timestamp: {datetime.now()}\nLevel: {level}\nPattern: {pattern}\nContext: {context}"
        
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = sender
        msg['To'] = receiver

        try:
            with smtplib.SMTP_SSL(host, port) as server:
                server.login(sender, app_pass)
                server.sendmail(sender, receiver, msg.as_string())
            print(f"📧 Email alert sent to {receiver}")
            logging.info(f"Email sent for: {pattern}")
        except Exception as e:
            print(f"❌ Email failed: {e}")
            logging.error(f"SMTP Error: {e}")

    def _process_logic(self, text, source_name, frame):
        for level, patterns in self.policies.items():
            for p in patterns:
                clean_p = str(p).lower()
                if clean_p in text.lower():
                    now = time.time()
                    if now - self.alert_history.get(clean_p, 0) > self.cooldown:
                        timestamp = datetime.now().strftime('%H:%M:%S')
                        print(f"🔴 [{level}] {timestamp} | Found '{clean_p}' in {source_name}")
                        
                        self.session_stats[level] += 1
                        self.alert_history[clean_p] = now
                        
                        logging.warning(f"DETECTION: {clean_p} | Source: {source_name}")
                        self._send_email(level, clean_p, source_name)
                        
                        img_path = f"alerts/alert_{datetime.now().strftime('%H%M%S')}.jpg"
                        cv2.imwrite(img_path, frame)

    def run(self):
        print("="*60)
        print("  AVSAS Professional - Monitoring Started")
        print(f"  Target Email: {self.email_cfg.get('receiver')}")
        print("="*60)
        try:
            while True:
                loop_start = time.time()
                screenshot = pyautogui.screenshot()
                frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)

                # Global Scan (กันเหนียวสำหรับ Terminal)
                full_text = pytesseract.image_to_string(frame, lang='eng+tha', config='--psm 6')
                self._process_logic(full_text, "Global Screen", frame)

                # YOLO Scan
                results = self.model(frame, conf=self.yolo_conf, verbose=False)
                for r in results:
                    for box in r.boxes:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        label = r.names[int(box.cls[0])]
                        roi = frame[max(0, y1):min(frame.shape[0], y2), max(0, x1):min(frame.shape[1], x2)]
                        if roi.size > 0:
                            roi_text = pytesseract.image_to_string(roi, lang='eng+tha')
                            self._process_logic(roi_text, f"Object:{label}", frame)

                cv2.imshow("AVSAS Monitor", results[0].plot())
                if cv2.waitKey(1) & 0xFF == ord('q'): break

                wait = self.interval - (time.time() - loop_start)
                if wait > 0: time.sleep(wait)
        finally:
            cv2.destroyAllWindows()

if __name__ == "__main__":
    auditor = AVSAS_Auditor()
    auditor.run()