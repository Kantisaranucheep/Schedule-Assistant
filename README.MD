to run for dev
1. เตรียม dokcer แต่ส่วนของ database กับ ollama พอ
2. path apps/backend
3. สร้าง env ชื่ออะไรก็ได้ แต่ใส่ใน gitignore ด้วยไม่ต้อง push มา
4. pip install -r requirement.txt
4. pip install websockets (กูอาจเขียน cmd ผิดลองเช็คก่อน)
5. unicorn app.main:app --reload (กูอาจเขียน cmd ผิดลองเช็คก่อน)
ุ6. frontend run เหมือนเดิม

รหัสที่ใช้ test
1. demo/ demo1234
2. testuser/ test1234