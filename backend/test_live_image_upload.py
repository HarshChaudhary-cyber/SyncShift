import io, json
from PIL import Image, ImageDraw
import httpx

def main():
    with httpx.Client() as client:
        r_login = client.post(
            'http://127.0.0.1:8000/api/v1/auth/login',
            json={'email': 'imagetest_user@syncshift.io', 'password': 'Password123!'}
        )
        assert r_login.status_code == 200, r_login.text
        token = r_login.json()['data']['token']

        # Generate sample timetable image
        img = Image.new('RGB', (800, 300), color=(255, 255, 255))
        d = ImageDraw.Draw(img)
        d.text((20, 30), 'SEMESTER TIMETABLE', fill=(0, 0, 0))
        d.text((20, 80), 'Tuesday 10:00 - 11:30 PHYS101 Room 101', fill=(0, 0, 0))
        d.text((20, 130), 'Thursday 13:00 - 14:30 CHEM102 Lab 4B', fill=(0, 0, 0))
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)

        files = {'file': ('timetable_schedule.png', buf, 'image/png')}
        headers = {'Authorization': f'Bearer {token}'}
        resp = client.post('http://127.0.0.1:8000/api/v1/import/file', files=files, headers=headers, timeout=30.0)

        print('HTTP STATUS:', resp.status_code)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        print('PARSED CLASSES COUNT:', len(data['data']['preview']))
        for item in data['data']['preview']:
            print(f" - {item['title']}: {item.get('day_name')} {item.get('start_time')} - {item.get('end_time')} (Status: {item.get('status')})")

if __name__ == '__main__':
    main()
