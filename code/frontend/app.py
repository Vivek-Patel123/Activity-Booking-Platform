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

@app.route('/admin/new-offering', methods=['GET', 'POST'])
def new_offering():
    if request.method == 'POST':
        title = request.form.get('title')
        location = request.form.get('location')
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        lesson_type = request.form.get('lesson_type')
        max_participants = request.form.get('max_participants') if lesson_type == 'group' else None

        # Create a new offering object
        offering_data = {
            'title': title,
            'location': location,
            'start_time': start_time,
            'end_time': end_time,
            'lesson_type': lesson_type,
            'booked_by': None if lesson_type == 'private' else None,
            'participants': 0 if lesson_type == 'group' else None,
            'max_participants': int(max_participants) if lesson_type == 'group' else None
        }

        # Save the offering data to Firebase
        db.reference('offerings').push(offering_data)

        flash("New offering created successfully!", "success")
        return redirect(url_for('index'))
    
    return render_template('new_offering.html')



@app.route('/offerings', methods=['GET', 'POST'])
def offerings():
    if request.method == 'POST':
        offering_id = request.form.get('offering_id')
        instructor_name = request.form.get('instructor_name')
        
        # Retrieve the offering data from Firebase
        offering_ref = db.reference(f'offerings/{offering_id}')
        offering_data = offering_ref.get()
        
        if offering_data:
            if offering_data.get('lesson_type') == 'private':
                # Private booking: Check if it's already booked
                if not offering_data.get('booked_by'):
                    offering_ref.update({'booked_by': instructor_name})
                    flash(f"Offering successfully booked by {instructor_name}", "success")
                else:
                    flash("This private offering has already been booked.", "error")
            elif offering_data.get('lesson_type') == 'group':
                # Group booking: Increment participant count
                current_participants = offering_data.get('participants', 0)
                max_participants = offering_data.get('max_participants')

                if current_participants < max_participants:
                    # Increment participants count
                    offering_ref.update({'participants': current_participants + 1})
                    flash(f"Offering successfully booked by {instructor_name}", "success")
                else:
                    flash("This group offering is fully booked.", "error")

        return redirect(url_for('offerings'))

    # Retrieve available offerings from the database
    offerings_ref = db.reference('offerings')
    offerings_data = offerings_ref.get() or {}
    
    # Convert offerings_data into a list for easier rendering
    offerings_list = []
    for offering_id, offering in offerings_data.items():
        offering['id'] = offering_id
        offerings_list.append({
            'title': offering.get('title'),
            'location': offering.get('location'),
            'start_time': offering.get('start_time'),
            'end_time': offering.get('end_time'),
            'lesson_type': offering.get('lesson_type'),
            'booked_by': offering.get('booked_by'),
            'participants': offering.get('participants', 0),
            'max_participants': offering.get('max_participants'),
            'id': offering_id
        })

    return render_template('offerings.html', offerings=offerings_list)

@app.route('/delete_offering', methods=['POST'])
def delete_offering():
    offering_id = request.form.get('offering_id')
    
    if offering_id:
        # Delete the offering from Firebase
        offering_ref = db.reference(f'offerings/{offering_id}')
        offering_ref.delete()
        flash("Offering deleted successfully.", "success")
    else:
        flash("Failed to delete offering.", "error")
    
    return redirect(url_for('offerings'))



if __name__ == '__main__':
    app.run(debug=True)
