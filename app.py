from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from pymongo import MongoClient
from bson import ObjectId
import os, datetime

app = Flask(__name__, static_folder='static')
CORS(app)

# ── MongoDB Connection ──────────────────────────────────────────
MONGO_URI = os.environ.get('MONGO_URI', '')
client     = MongoClient(MONGO_URI)
db         = client['vendor_db']
col        = db['vendors']

# สร้าง index ให้ค้นหาเร็ว
col.create_index('id', unique=True)

def fmt(v):
    v.pop('_id', None)
    return v

# ── routes ─────────────────────────────────────────────────────────
@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/api/vendors', methods=['GET'])
def get_vendors():
    vendors = list(col.find({}, {'_id': 0}))
    return jsonify(vendors)

@app.route('/api/vendors', methods=['POST'])
def add_vendor():
    v = request.json
    if not v.get('id') or not v.get('name') or not v.get('phone'):
        return jsonify({'error': 'ข้อมูลไม่ครบ'}), 400
    if col.find_one({'id': v['id']}):
        return jsonify({'error': 'Vendor ID นี้มีอยู่แล้ว'}), 409
    v['updated'] = datetime.date.today().isoformat()
    v['status']  = v.get('status', 'Active')
    col.insert_one(v)
    return jsonify({'ok': True, 'vendor': fmt(v)}), 201

@app.route('/api/vendors/<vid>', methods=['PUT'])
def update_vendor(vid):
    data = request.json
    data['id']      = vid
    data['updated'] = datetime.date.today().isoformat()
    result = col.replace_one({'id': vid}, data)
    if result.matched_count == 0:
        return jsonify({'error': 'ไม่พบ Vendor'}), 404
    return jsonify({'ok': True, 'vendor': data})

@app.route('/api/vendors/<vid>', methods=['DELETE'])
def delete_vendor(vid):
    result = col.delete_one({'id': vid})
    if result.deleted_count == 0:
        return jsonify({'error': 'ไม่พบ Vendor'}), 404
    return jsonify({'ok': True, 'deleted': vid})

@app.route('/api/stats', methods=['GET'])
def stats():
    vendors = list(col.find({}, {'_id': 0}))
    total   = len(vendors)
    cats    = {}
    for v in vendors:
        c = v.get('cat') or '(ไม่ระบุ)'
        cats[c] = cats.get(c, 0) + 1
    return jsonify({
        'total':        total,
        'miss_email':   sum(1 for v in vendors if not v.get('email')),
        'miss_cat':     sum(1 for v in vendors if not v.get('cat')),
        'miss_region':  sum(1 for v in vendors if not v.get('region')),
        'miss_phone':   sum(1 for v in vendors if not v.get('phone')),
        'miss_contact': sum(1 for v in vendors if not v.get('contact')),
        'miss_addr':    sum(1 for v in vendors if not v.get('addr', '')),
        'categories':   cats,
    })

# ── นำเข้าข้อมูลเดิมจาก JSON (รันครั้งแรกครั้งเดียว) ──────────
@app.route('/api/import', methods=['POST'])
def import_data():
    data = request.json
    if not isinstance(data, list):
        return jsonify({'error': 'ต้องส่งเป็น array'}), 400
    inserted = 0
    for v in data:
        if not col.find_one({'id': v.get('id')}):
            col.insert_one(v)
            inserted += 1
    return jsonify({'ok': True, 'inserted': inserted})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
