
from flask import Flask, render_template, request, session, send_file, jsonify
import logging
import os
import io

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

app = Flask(__name__)

# Secret key for session management
app.secret_key = os.environ.get(
    "SECRET_KEY",
    "local-development-secret-key"
)

# Configure logging
logging.basicConfig(level=logging.INFO)


def safe_float(val):
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0


def calculate_emergency_fund(salary, expenses, months):
    total_monthly_expenses = sum(expenses.values())
    return round(total_monthly_expenses * months, 2)


def calculate_savings_ratio(salary, total_expenses):
    if salary > 0:
        return round(
            (salary - total_expenses) / salary * 100, 2
        )
    return 0


def generate_cost_cutting_tips(salary, expenses):
    tips = []

    for category, amount in expenses.items():
        if salary > 0 and amount > 0.2 * salary:
            tips.append(
                f"Consider cutting down on {category}, "
                "it's a major part of your salary."
            )

    if not tips:
        tips.append("Your expenses look balanced. Good job!")

    return tips


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/calculate', methods=['POST'])
def calculate():
    try:
        salary = safe_float(request.form.get('salary'))

        expenses = {
            'Rent': safe_float(request.form.get('Rent')),
            'Utilities': safe_float(request.form.get('Utilities')),
            'Groceries': safe_float(request.form.get('Groceries')),
            'Transport': safe_float(request.form.get('Transport')),
            'Insurance': safe_float(request.form.get('Insurance')),
            'Other': safe_float(request.form.get('Other')),
        }

        months = int(request.form.get('months') or 6)

        # Validate user input
        if salary <= 0:
            return "Please enter a valid positive monthly salary.", 400

        if any(amount < 0 for amount in expenses.values()):
            return "Expenses cannot be negative.", 400

        if months < 1 or months > 24:
            return "Months must be between 1 and 24.", 400

        total_monthly_expenses = sum(expenses.values())

        emergency_fund = calculate_emergency_fund(
            salary, expenses, months
        )

        savings_ratio = calculate_savings_ratio(
            salary, total_monthly_expenses
        )

        tips = generate_cost_cutting_tips(salary, expenses)

        labels = list(expenses.keys())
        values = list(expenses.values())

        logging.info(
            f"Salary: {salary}, "
            f"Expenses: {total_monthly_expenses}, "
            f"Emergency Fund: {emergency_fund}, "
            f"Savings Ratio: {savings_ratio}"
        )

        # Store calculation history in session
        if 'history' not in session:
            session['history'] = []

        session['history'].append({
            'salary': salary,
            'expenses': expenses,
            'months': months,
            'emergency_fund': emergency_fund,
            'savings_ratio': savings_ratio
        })

        session.modified = True

        return render_template(
            'result.html',
            salary=salary,
            total_monthly_expenses=total_monthly_expenses,
            emergency_fund=emergency_fund,
            savings_ratio=savings_ratio,
            months=months,
            expenses=expenses,
            tips=tips,
            labels=labels,
            values=values
        )

    except (ValueError, TypeError):
        return "Invalid input. Please check your entries.", 400

    except Exception:
        logging.exception("An error occurred during calculation.")
        return "Something went wrong. Please try again.", 500


@app.route('/download-pdf')
def download_pdf():
    try:
        if not session.get('history'):
            return "No data available for report generation.", 404

        last_entry = session['history'][-1]

        buffer = io.BytesIO()

        pdf = canvas.Canvas(buffer, pagesize=letter)

        pdf.setFont("Helvetica", 12)

        pdf.drawString(100, 750, "Emergency Fund Report")
        pdf.line(100, 747, 500, 747)

        y = 720

        pdf.drawString(
            100, y,
            f"Monthly Salary: INR {last_entry['salary']}"
        )
        y -= 20

        pdf.drawString(
            100, y,
            f"Months to Save: {last_entry['months']}"
        )
        y -= 20

        pdf.drawString(
            100, y,
            f"Emergency Fund Required: INR "
            f"{last_entry['emergency_fund']}"
        )
        y -= 20

        pdf.drawString(
            100, y,
            f"Savings Ratio: {last_entry['savings_ratio']}%"
        )

        y -= 40

        pdf.drawString(100, y, "Monthly Expenses:")

        for category, amount in last_entry['expenses'].items():
            y -= 20

            pdf.drawString(
                120, y,
                f"{category}: INR {amount}"
            )

        pdf.showPage()
        pdf.save()

        buffer.seek(0)

        return send_file(
            buffer,
            as_attachment=True,
            download_name='EmergencyFundReport.pdf',
            mimetype='application/pdf'
        )

    except Exception:
        logging.exception("Failed to generate PDF.")
        return "Error generating PDF report.", 500


@app.route('/history')
def view_history():
    return jsonify(session.get('history', []))


if __name__ == '__main__':
    app.run(debug=False)
