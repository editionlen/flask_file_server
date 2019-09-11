from flask import Flask, request, jsonify, render_template, Response
import os
import mimetypes
import re

FILE_UPLOAD_MAXSIZE = 1024 * 1024 * 100
MAX_CONTENT_LENGTH = FILE_UPLOAD_MAXSIZE + 1024
#下载文件不存在
FILE_NOT_FOUND_PAGE = "<html><head><title>File not found</title></head><body>File not found</body></html>"

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
UPLOAD_DIR = 'e://flask-project/file_svr/picture/'
REASON_SUCCESS = 'Success'
UPLOAD_OK_HTML="<html><head><title>File upload success</title></head><body>File upload success</body></html>"
cmd2dir = {"POST_CAPACITY_TOOL":"pic",
           "RECORDKEYADAPTER": "keyadapterbg",
           "POST_APP": "apk"}

@app.route('/', methods=['POST', 'GET'])
def upload():
    if request.method == 'POST':
        file = request.files.getlist('filename')[0]
        filename = file.filename
        # uploadtype(POST_CAPACITY_TOOL, RECORDKEYADAPTER, POST_APP, None)
        # 上传键值映射方案的背景图片RECORDKEYADAPTER包括 APPPACKAGENAME APPNAME VERSIONCODE DEVVER 上传到目录 keyadapterbg
        # 上传智能游戏助手APP的工具图片POST_CAPACITY_TOOL 上传到目录 pic
        # None则保存到根目录
        # picname 如果有的话，则文件名使用picname
        newfilename = request.form.get("picname")
        if newfilename:
            filename = newfilename
        upload_type = request.form.get("uploadtype")
        if upload_type:
            newdir = cmd2dir.get(upload_type, "oth") + '/'
        else:
            newdir = ''
        savepath = os.getcwd() + '/picture/' + newdir + filename
        file.save(savepath)
        return UPLOAD_OK_HTML
    return render_template('index.html')

@app.route('/upload/')
def upload_top():
    return render_template('upload.html')

@app.route('/upload_keyapdate/')
def upload_keyapdater():
    return render_template('keyadapterbg.html')

@app.route('/upload_capacity/')
def upload_capacity():
    return render_template('capacity_tool.html')

@app.route('/upload_file_size_limit/')
def upload_file_size_limit():
    return jsonify(dict(maxsize=FILE_UPLOAD_MAXSIZE, unit='B'))

#分段上传文件
@app.route('/block_upload/', methods=['POST', 'GET'])
def block_upload():
    if request.method == 'POST':
        try:
            file = request.files.getlist('file')[0]
            filename = request.form.get("filename")
            chunk_num = request.form.get('chunk_num')
            timestamp = request.form.get('timestamp')
            filename = '{}-{}-{}.tmp'.format(filename, timestamp,chunk_num)
            file.save(UPLOAD_DIR + filename)
            return UPLOAD_OK_HTML, 200
        except Exception as e:
            print('e:',e)
            return e, 500
    return render_template('block_upload.html')

#合并分段上传文件
@app.route('/block_merge/', methods=['POST'])
def block_merge():
    if request.method == 'POST':
        filename = request.form.get("filename")
        picname = request.form.get("picname")
        chunk_count = int(request.form.get("chunk_count"))
        timestamp = request.form.get('timestamp')
        result = None
        if picname:
            result_filename = UPLOAD_DIR + picname
        else:
            result_filename = UPLOAD_DIR + filename
        tmp_filename = result_filename + '.tmp'
        with open(tmp_filename, 'wb') as target_file:  # 创建新文件
            for i in range(1, chunk_count + 1):
                try:
                    chunk_filename = UPLOAD_DIR + '{}-{}-{}.tmp'.format(filename, timestamp, i)
                    source_file = open(chunk_filename, 'rb')  # 按序打开每个分片
                    target_file.write(source_file.read())  # 读取分片内容写入新文件
                    source_file.close()
                except IOError as io_error:
                    print('merge', io_error)
                    result = '{}'.format(io_error)
                    break
                os.remove(chunk_filename)  # 删除该分片，节约空间
        if result:
            return result, 500
        else:
            if os.path.exists(result_filename):
                os.remove(result_filename)
            os.rename(tmp_filename, result_filename)
            return UPLOAD_OK_HTML, 200

#多文件上传
@app.route('/multi_files/', methods=['GET', 'POST'])
def multi_files():
    if request.method == 'POST':
        try:
            files = request.files.getlist('file')
            print('files has', len(files))
            for f in files:
                print(UPLOAD_DIR + f.filename)
                f.save(UPLOAD_DIR + f.filename)
            return UPLOAD_OK_HTML, 200
        except Exception as e:
            return e, 500
    else:
        return render_template('multi_files.html')

@app.route('/<path:filename>')
def show(filename):
    if request.method == 'GET':
        path_filename = os.path.join(UPLOAD_DIR, filename)
        if os.path.isfile(path_filename):
            if 'Range' in request.headers:
                start, end = get_range()
            else:
                start, end = 0, None
            resp = partial_response(path_filename, start, end)
            return resp
    return FILE_NOT_FOUND_PAGE

def partial_response(path, start, end=None):
    file_size = os.path.getsize(path)
    if end is None:
        end = file_size - 1
    end = min(end, file_size - 1)
    length = end - start + 1

    if end == file_size - 1:
        code = 200
    else:
        code = 206

    with open(path, 'rb') as fd:
        fd.seek(start)
        bytes = fd.read(length)
    assert len(bytes) == length

    content_types = mimetypes.guess_type(path)
    if content_types is None:
        content_type = 'text/plain;charset=UTF-8'
    else:
        content_type = content_types[0]
        if content_type == 'text/plain':
            content_type = content_type + ';charset=UTF-8'

    response = Response(
        bytes,
        code,
        mimetype=content_type,
        direct_passthrough=True,
    )
    response.headers.add(
        'Content-Range', 'bytes {0}-{1}/{2}'.format(
            start, end, file_size,
        ),
    )
    response.headers.add(
        'Accept-Ranges', 'bytes'
    )
    if content_types[0] is None:
        response.headers.add("Content-Disposition", "attachment;")
    return response

def get_range():
    range = request.headers.get('Range')
    m = re.match('bytes=(?P<start>\d+)-(?P<end>\d+)?', range)
    if m:
        start = m.group('start')
        end = m.group('end')
        start = int(start)
        if end is not None:
            end = int(end)
        return start, end
    else:
        return 0, None

if __name__ == '__main__':
    app.run()