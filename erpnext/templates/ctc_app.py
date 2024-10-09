from flask import Flask, render_template, request

app = Flask(__name__)

# Function to calculate CTC
def calculate_ctc(basic_salary, hra, special_allowance, epf_employee, professional_tax, income_tax):
    # Gratuity Calculation (Basic Salary * 4.81%)
    gratuity = basic_salary * 0.0481

    # CTC Calculation
    annual_ctc = (basic_salary + hra + special_allowance) * 12
    
    # Deductions
    total_deductions = (basic_salary * epf_employee / 100 * 12) + professional_tax + income_tax
    
    # Net Take-Home Calculation
    net_take_home = (basic_salary + hra + special_allowance) * 12 - total_deductions
    
    return {
        "annual_ctc": annual_ctc,
        "gratuity": gratuity,
        "total_deductions": total_deductions,
        "net_take_home": net_take_home
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/calculate', methods=['POST'])
def calculate():
    try:
        # Get inputs from the form
        basic_salary = float(request.form['basic_salary'])
        hra = float(request.form['hra'])
        special_allowance = float(request.form['special_allowance'])
        epf_employee = float(request.form['epf_employee'])
        professional_tax = float(request.form['professional_tax'])
        income_tax = float(request.form['income_tax'])
        
        # Calculate CTC
        result = calculate_ctc(basic_salary, hra, special_allowance, epf_employee, professional_tax, income_tax)

        return render_template('result.html', result=result)
    except Exception as e:
        return str(e)

if __name__ == '__main__':
    app.run(debug=True)
