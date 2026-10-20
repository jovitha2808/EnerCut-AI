from pathlib import Path
from flask import Flask, render_template, request, make_response
from src.optimizer import load_data, recommend_top3
import csv, io

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / 'data' / 'Ti6Al4V_ELI_turning_experimental_dataset.xlsx'
app = Flask(__name__)
df = load_data(DATA_PATH)

@app.route('/', methods=['GET', 'POST'])
def index():
    results = None
    error = None
    form = {'tool': sorted(df['tool'].unique())[0], 'diameter': '40', 'angle': '80'}
    if request.method == 'POST':
        form = {'tool': request.form.get('tool', form['tool']),
                'diameter': request.form.get('diameter', '40'),
                'angle': request.form.get('angle', '80')}
        try:
            diameter = float(form['diameter'])
            angle = float(form['angle'])
            if not 1 <= diameter <= 1000:
                raise ValueError('Workpiece diameter must be between 1 and 1000 mm.')
            if not 1 <= angle <= 179:
                raise ValueError('Approach angle must be between 1 and 179 degrees.')
            result = recommend_top3(df, form['tool'], diameter, angle)
            results = result.round(4).to_dict(orient='records')
            if not results:
                error = 'No observed machining conditions were found for this tool grade.'
        except Exception as exc:
            error = str(exc)
    return render_template('index.html', tools=sorted(df['tool'].unique()), form=form,
                           results=results, error=error)

@app.route('/download', methods=['POST'])
def download():
    try:
        tool = request.form.get('tool', sorted(df['tool'].unique())[0])
        diameter = float(request.form.get('diameter', '40'))
        angle = float(request.form.get('angle', '80'))
        result = recommend_top3(df, tool, diameter, angle)
        buffer = io.StringIO()
        result.to_csv(buffer, index=False)
        response = make_response(buffer.getvalue())
        response.headers['Content-Disposition'] = 'attachment; filename=enercut_top3_recommendations.csv'
        response.headers['Content-Type'] = 'text/csv; charset=utf-8'
        return response
    except Exception as exc:
        return str(exc), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
