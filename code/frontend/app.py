from flask import Flask, render_template, request, redirect, url_for, flash
import firebase_admin
from firebase_admin import db, credentials

cred = credentials.Certificate("credentials.json")
firebase_admin.initialize_app(cred, {"databaseURL": "https://soen342-929fb-default-rtdb.firebaseio.com"})

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

        # Create a new offering object
        offering_data = {
            'title': title,
            'location': location,
            'start_time': start_time,
            'end_time': end_time,
            'lesson_type': lesson_type
        }

        # Save the offering data to Firebase
        db.reference('offerings').push(offering_data)

        flash("New offering created successfully!", "success")
        return redirect(url_for('index'))
    
    return render_template('new_offering.html')

# Route for viewing and accepting offerings (for instructors)
@app.route('/offerings', methods=['GET', 'POST'])
def offerings():
    if request.method == 'POST':
        # Process offering selection (e.g., instructor accepts offering)
        offering_id = request.form.get('offering_id')
        # Handle acceptance logic here (e.g., mark offering as accepted in the database)

    # Retrieve available offerings from the database
    offerings_ref = db.reference('offerings')
    offerings_data = offerings_ref.get() or {}  # Retrieve offerings or return empty dict if none
    
    # Convert offerings_data into a list for easier rendering
    offerings_list = []
    for offering_id, offering in offerings_data.items():
        offering['id'] = offering_id  # Add the ID to each offering dictionary
        offerings_list.append({
            'title': offering.get('title'),
            'location': offering.get('location'),
            'start_time': offering.get('start_time'),
            'end_time': offering.get('end_time'),
            'lesson_type': offering.get('lesson_type'),
            'id': offering_id
        })

    return render_template('offerings.html', offerings=offerings_list)

if __name__ == '__main__':
    app.run(debug=True)
