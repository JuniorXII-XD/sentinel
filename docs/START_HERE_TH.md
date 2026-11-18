# เริ่มใช้ SENTINEL Standard

โปรเจกต์นี้มี Backend และฐานข้อมูลจริง หน้าเว็บจะไม่ทำงานด้วยการดับเบิลคลิก `index.html` ต้องเปิดเซิร์ฟเวอร์ก่อน แนะนำให้เริ่มบนคอมพิวเตอร์ Windows, macOS หรือ Linux

## 1. เตรียมเครื่อง

ติดตั้ง Python 3.12 และ Node.js 22.12 ขึ้นไป แล้วแตก ZIP เปิด Terminal ในโฟลเดอร์ `sentinel` ตรวจด้วย `python --version` และ `node --version` บางเครื่องใช้ `python3` แทน `python`

```bash
python -m venv .venv
```

เปิดสภาพแวดล้อม Python:

- Windows PowerShell: `.venv\Scripts\Activate.ps1`
- Windows Command Prompt: `.venv\Scripts\activate.bat`
- macOS / Linux: `source .venv/bin/activate`

ถ้า PowerShell ไม่อนุญาตสคริปต์ ให้ใช้ Command Prompt แทน ไม่จำเป็นต้องปิดระบบรักษาความปลอดภัยของเครื่อง

```bash
pip install -r backend/requirements.txt
npm --prefix frontend ci
npm --prefix frontend run build
cd backend
```

คัดลอก `.env.example` เป็น `.env` ด้วยโปรแกรมจัดการไฟล์ แล้วรัน:

```bash
alembic upgrade head
python -m app.cli create-user --username admin --role admin
```

ตั้งรหัสผ่านส่วนตัว 12–128 ตัวอักษร ขณะพิมพ์รหัสผ่านจะไม่แสดงบนหน้าจอ เป็นพฤติกรรมปกติ **ไม่มีรหัสผ่านสำเร็จรูปในไฟล์**

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-proxy-headers
```

เปิด http://127.0.0.1:8000 แล้วเข้าสู่ระบบด้วยบัญชีที่เพิ่งสร้าง ห้ามปิด Terminal ระหว่างใช้งาน กด Ctrl+C เพื่อหยุดเซิร์ฟเวอร์

## 2. สร้างข้อมูลสาธิต

แก้ `.env` เป็น `DEMO_ENABLED=true` โดยคง `ENVIRONMENT=development` แล้วเริ่มเซิร์ฟเวอร์ใหม่ เข้าสู่ระบบ Admin → Settings → Generate demo events จากนั้นเลือก **Demo dataset** บนแถบด้านบน

ข้อมูลสาธิตเกิดจากโค้ดสร้างเหตุการณ์และ Detection Engine จริง แล้วบันทึกลงฐานข้อมูล ไม่ใช่ค่าคงที่ที่หน้า Dashboard ใช้หลอกแสดงผล มีป้าย Demo ชัดเจนและไม่ปะปนกับ Live events

กดสร้างซ้ำจะไม่เพิ่มข้อมูลชุดเดิมอีก ถ้าต้องการเริ่มชุดใหม่ ให้สร้างฐานข้อมูลแล็บอีกไฟล์ผ่าน `DATABASE_URL` แล้ว migrate และสร้างบัญชีใหม่ แทนการลบฐานข้อมูลที่มีข้อมูลสำคัญ

## 3. ทดลองใช้งานแต่ละส่วน

| หน้า | สิ่งที่ทดลอง |
| --- | --- |
| Overview | สลับ Live/Demo และช่วง 1/7/30/90 วัน ตรวจว่าตัวเลขเปลี่ยนตามข้อมูล |
| Security events | ค้นหา `192.0.2.42`, เลือกประเภทเหตุการณ์หรือ Severity |
| Threat alerts | เปิด Alert → ดูหลักฐาน → เปลี่ยนเป็น Investigating พร้อมหมายเหตุ → Resolved |
| Analytics | เปรียบเทียบจำนวน Login สำเร็จ/ล้มเหลวและสัดส่วน Alert |
| Reports | Export CSV และ PDF แล้วเทียบค่ากับรายงานบนหน้าเว็บ |
| Settings | ดูเงื่อนไข 5 กฎ เปิด/ปิดกฎ และสร้างบัญชี Analyst |

Analyst อ่านข้อมูลและส่งออกรายงานได้ แต่แก้ Alert, บัญชี หรือกฎไม่ได้ Backend ตรวจสิทธิ์จริง ไม่ได้อาศัยแค่ซ่อนปุ่ม

## 4. สาธิตภายใน 5 นาที

1. อธิบายว่าโจทย์คือธุรกิจต้องการมองเห็นความผิดปกติจากข้อมูล Login และสิทธิ์การเข้าถึง
2. เข้าสู่ระบบ Admin เปิด Demo dataset แสดงภาพรวมและค้นหา IP ตัวอย่าง
3. เปิด Repeated login failures อธิบาย “ล้มเหลวอย่างน้อย 5 ครั้งใน 60 วินาที” พร้อมชี้หลักฐาน
4. เปลี่ยนเป็น Investigating ใส่เหตุผล แล้ว Resolved ให้เห็นประวัติที่ยังอยู่
5. เปิด Reports ส่งออก PDF และอธิบายว่าจะใช้สื่อสารความเสี่ยงกับผู้ดูแลธุรกิจอย่างไร
6. แสดงผลเทสต์ แล้วบอกข้อจำกัดว่า Alert ยังต้องให้คนตรวจสอบ ไม่ใช่การยืนยันการโจมตี

## 5. รันเทสต์ด้วยตัวเอง

จากโฟลเดอร์ `backend` และเปิด virtual environment แล้ว:

```bash
python -m pytest -q
alembic check
cd ../frontend
npm test
npm run build
```

Pytest ใช้ฐานข้อมูลชั่วคราวที่แยกจากงานของเรา Frontend tests ใช้ jsdom จำลอง DOM จึงไม่ใช่หลักฐานว่าทดสอบบนมือถือจริงแล้ว ผลที่ตรวจจริงและสิ่งที่ยังไม่ตรวจอยู่ใน `docs/TEST_REPORT.md`

## 6. ปัญหาที่พบบ่อย

| อาการ | วิธีตรวจ |
| --- | --- |
| ไม่มีคำสั่ง `uvicorn` / `alembic` | เปิด virtual environment และติดตั้ง requirements |
| ไม่มีตารางในฐานข้อมูล | รัน `alembic upgrade head` จาก `backend` |
| หน้าเว็บ 404 | Build Frontend ก่อนเริ่ม FastAPI แล้ว restart |
| Untrusted or missing Origin | ใช้ URL ให้ตรง `TRUSTED_ORIGINS` ทุกตัวอักษร รวม protocol และ port; ไม่มี `/` ท้าย origin |
| Login ได้แต่ไม่ส่ง Cookie | ถ้ารัน HTTP ในเครื่องใช้ `COOKIE_SECURE=false`; HTTPS Production ต้องเป็น true |
| Too many attempts | รอครบหน้าต่าง 5 นาที อย่าลองรัว ๆ |
| Demo dataset ไม่ขึ้น | เปิด `DEMO_ENABLED=true`, ใช้ development, restart และ Login ใหม่ |
| Alert changed | มีการแก้ Alert หลังจากเปิดหน้า ให้ Refresh แล้วตรวจข้อมูลก่อนบันทึก |
| Database is locked | ตรวจว่ามีโปรเซสรันซ้ำหรือ migration ระหว่างใช้งานหรือไม่; SQLite เหมาะกับแล็บขนาดเล็ก |

รีเซ็ตรหัสผ่านจาก Terminal ภายในเครื่อง: `python -m app.cli reset-password --username admin` การรีเซ็ตทำให้ Session เดิมใช้ไม่ได้

## 7. การเปิดจากโทรศัพท์และการนำขึ้นออนไลน์

โค้ดมี responsive layout แต่รอบนี้ยังไม่ได้ตรวจภาพและการใช้งานจริงบนโทรศัพท์ อย่าอ้างว่าผ่าน mobile end-to-end testing แล้ว มีรายการตรวจใน `docs/MANUAL_QA.md`

ค่าเริ่มต้น bind เฉพาะ localhost เพื่อใช้เป็นแล็บ การเปิดเข้าจากเครือข่ายหรือขึ้นอินเทอร์เน็ตต้องจัด HTTPS, origins, hosts, firewall และ database ให้เหมาะสมก่อน ไม่ควรเปลี่ยนเป็น `0.0.0.0` แล้วเปิดพอร์ตสาธารณะทันที

รอบนี้ไม่ได้ Deploy สาธารณะ เนื่องจากโฮสต์เว็บไซต์ที่มีให้ใช้ไม่รองรับ Python/FastAPI โดยตรง ไฟล์ Docker เป็นทางเลือกสำหรับสภาพแวดล้อมที่รองรับ container แต่ยังไม่ได้ทดสอบการ build Docker ที่นี่

## อัปเกรดจาก Standard 1.0 เป็น 1.0.1

หยุดเซิร์ฟเวอร์และสำรองฐานข้อมูลให้ครบก่อน เปลี่ยนไฟล์โปรแกรมโดยเก็บ `.env` และฐานข้อมูลเดิมไว้ จากโฟลเดอร์ `backend` ที่เปิด virtual environment แล้ว รัน:

```bash
alembic upgrade head
```

จากโฟลเดอร์ `sentinel` รัน `npm --prefix frontend ci` และ `npm --prefix frontend run build` แล้วเปิดเซิร์ฟเวอร์อีกครั้ง ไม่ต้องสร้างบัญชีใหม่หรือ seed ข้อมูลซ้ำ

แพตช์นี้ทำให้เปิดหน้า Login แล้วไม่เพิ่ม High-risk event จาก `/auth/me` และจำกัด Login ตามคู่ username+IP แทนการล็อกชื่อบัญชีจากทุกแหล่งพร้อมกัน ส่วนเหตุการณ์เก่าที่เกิดจากข้อบกพร่องยังเก็บไว้ตามเดิม จึงอาจเห็นยอดเก่าในช่วงวันที่เลือก

ค่าตัวเลขกฎใน Settings เป็นแบบอ่านอย่างเดียว และแสดงค่าจากฐานข้อมูล ผู้ดูแลเปิด/ปิดกฎได้ ส่วนการเปลี่ยนตัวเลขให้ทำผ่าน migration ที่ตรวจสอบแล้ว เหมาะสำหรับใช้เป็นแล็บส่วนตัวเพื่อศึกษาผลของกฎแต่ละข้อ รายละเอียดการแก้และข้อจำกัดอยู่ใน `docs/REVIEW_FIXES.md`
