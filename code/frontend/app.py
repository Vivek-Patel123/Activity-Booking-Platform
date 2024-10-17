from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__, template_folder='templates')

app.secret_key = 'your_secret_key'  # for session management, flash messages, etc.

# Homepage route
@app.route('/')
def index():
    return render_template('index.html')

# Route for creating a new offering (for admin)
@app.route('/admin/new-offering', methods=['GET', 'POST'])
def new_offering():
    if request.method == 'POST':
        title = request.form.get('title')
        location = request.form.get('location')
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        lesson_type = request.form.get('lesson_type')
        # Save to database (function not yet defined)
        flash("New offering created successfully!", "success")
        return redirect(url_for('index'))
    return render_template('new_offering.html')

# Route for viewing and accepting offerings (for instructors)
@app.route('/offerings', methods=['GET', 'POST'])
def offerings():
    if request.method == 'POST':
        # Process offering selection (e.g., instructor accepts offering)
        pass
    # Render available offerings
    offerings_list = []  # Replace with a call to retrieve offerings from database
    return render_template('offerings.html', offerings=offerings_list)

if __name__ == '__main__':
    app.run(debug=True)
