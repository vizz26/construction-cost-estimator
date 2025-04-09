import tkinter as tk
from tkinter import messagebox, filedialog
from tkinter import ttk
from fpdf import FPDF
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from tkcalendar import Calendar, DateEntry
from datetime import date, datetime
import unicodedata
import re
from pymongo import MongoClient

# MongoDB Connection
try:
    client = MongoClient("mongodb://localhost:27017/")
    db = client["constructionestimator"]
    collection = db["quotations"]
    print("✅ Connected to MongoDB successfully")
except Exception as e:
    print(f"❌ Failed to connect to MongoDB: {e}")

def save_quotation():
    try:
        email = email_entry.get().strip().lower()
        customer_name = entry_customer_name.get().strip()
        building_site = entry_building_site.get().strip()
        validity_date = entry_validity_date.get().strip()

        if not email or not customer_name or not building_site or not validity_date:
            messagebox.showerror("Input Error", "All fields are required!")
            return

        # Extract Floors and Extra Works from Text Display
        floors = []
        extra_works = []
        content = text_display.get("1.0", tk.END).strip()

        for line in content.splitlines():
            if "Floor Name:" in line:
                try:
                    parts = re.search(r"Floor Name: (.*?), (.*?) sqft X ₹(.*?) = ₹(.*?)$", line)
                    if parts:
                        floor_name = parts.group(1).strip()
                        area_sqft = float(parts.group(2).strip())
                        cost_per_sqft = float(parts.group(3).strip())
                        total_cost = float(parts.group(4).replace("₹", "").replace(",", "").strip())

                        floors.append({
                            "name": floor_name,
                            "area_sqft": area_sqft,
                            "cost_per_sqft": cost_per_sqft,
                            "total_cost": total_cost
                        })
                except Exception as e:
                    print(f"❌ Error processing floor data: {line} - {e}")

            if "Extra Works:" in line:
                try:
                    parts = re.search(r"Extra Works: (.*?), Qty: (.*?) @ ₹(.*?) = ₹(.*?)$", line)
                    if parts:
                        work_name = parts.group(1).strip()
                        quantity = int(parts.group(2).strip())
                        cost_per_unit = float(parts.group(3).replace("₹", "").strip())
                        total_cost = float(parts.group(4).replace("₹", "").replace(",", "").strip())

                        extra_works.append({
                            "name": work_name,
                            "quantity": quantity,
                            "cost_per_unit": cost_per_unit,
                            "total_cost": total_cost
                        })
                except Exception as e:
                    print(f"❌ Error processing extra works data: {line} - {e}")

        total_project_cost = sum(floor["total_cost"] for floor in floors) + sum(work["total_cost"] for work in extra_works)

        quotation_data = {
            "email": email,
            "customer_name": customer_name,
            "building_site": building_site,
            "validity_date": validity_date,
            "floors": floors,
            "extra_works": extra_works,
            "total_project_cost": total_project_cost
        }

        result = collection.insert_one(quotation_data)
        
        if result.inserted_id:
            messagebox.showinfo("Success", "Quotation saved successfully!")
            print("✅ Quotation stored successfully with ID:", result.inserted_id)
        else:
            print("❌ Data insertion failed!")
    
    except Exception as e:
        print(f"❌ Error saving quotation: {e}")
        messagebox.showerror("Database Error", f"An error occurred while saving the quotation: {e}")

def fetch_quotation():
    try:
        email = fetch_email_entry.get().strip().lower()

        if not email:
            messagebox.showerror("Input Error", "Please enter an email address.")
            return

        print(f"🔍 Searching for all quotations with email: {email}")

        results = collection.find({"email": email})  # Fetch all quotations with the given email

        text_display.delete("1.0", "end")  # Clear display before showing results
        found = False

        for result in results:
            found = True
            text_display.insert("end", f"🔹 Quotation ID: {result.get('_id', 'N/A')}\n")
            text_display.insert("end", f"Customer Name: {result.get('customer_name', 'N/A')}\n")
            text_display.insert("end", f"Building Site: {result.get('building_site', 'N/A')}\n")
            text_display.insert("end", f"Validity Date: {result.get('validity_date', 'N/A')}\n\n")

            # Display Floors
            text_display.insert("end", "🏢 Floors:\n")
            for floor in result.get("floors", []):
                text_display.insert("end", f" - {floor['name']}: {floor['area_sqft']} sqft x ₹{floor['cost_per_sqft']} = ₹{floor['total_cost']}\n")

            # Display Extra Works
            text_display.insert("end", "\n🔧 Extra Works:\n")
            for work in result.get("extra_works", []):
                text_display.insert("end", f" - {work['name']}: Qty {work['quantity']} @ ₹{work['cost_per_unit']} = ₹{work['total_cost']}\n")

            # Display Total Cost
            text_display.insert("end", f"\n💰 Total Project Cost: ₹{result.get('total_project_cost', 0)}\n")
            text_display.insert("end", "------------------------------------------------------------\n\n")

        if not found:
            print("❌ No quotations found.")
            messagebox.showwarning("Not Found", "No quotations found for this email.")

    except Exception as e:
        print(f"❌ Error fetching quotations: {e}")
        messagebox.showerror("Database Error", f"An error occurred while fetching the quotations: {e}")


def add_floor_info():
    try:
        floor_name = entry_floor_name.get().strip()
        area_sqft = entry_area_sqft.get().strip()
        cost_per_sqft = entry_cost_per_sqft.get().strip()

        # Validate inputs
        if not floor_name:
            messagebox.showerror("Input Error", "Floor name cannot be empty.")
            return
        if not area_sqft or not cost_per_sqft:
            messagebox.showerror("Input Error", "Enter valid numerical values.")
            return

        # Convert to float
        area_sqft = float(area_sqft)
        cost_per_sqft = float(cost_per_sqft)

        # Calculate cost
        area_cost = area_sqft * cost_per_sqft
        result = f"Floor Name: {floor_name}, {area_sqft} sqft X ₹{cost_per_sqft} = ₹{area_cost:.2f}\n{'-'*40}\n"
        
        # Insert into text display
        text_display.insert(tk.END, result)
        
        # Update total cost
        update_total()

        # Clear inputs
        entry_floor_name.delete(0, tk.END)
        entry_area_sqft.delete(0, tk.END)
        entry_cost_per_sqft.delete(0, tk.END)

    except ValueError:
        messagebox.showerror("Input Error", "Please enter valid numerical values.")

def add_extra_work_info():
    try:
        extra_works = entry_extra_works.get().strip()
        quantity = entry_quantity.get().strip()
        cost_per_quantity = entry_cost_per_quantity.get().strip()

        # Validate inputs
        if not extra_works:
            messagebox.showerror("Input Error", "Extra works name cannot be empty.")
            return
        if not quantity or not cost_per_quantity:
            messagebox.showerror("Input Error", "Enter valid numerical values.")
            return

        # Convert to appropriate types
        quantity = int(quantity)
        cost_per_quantity = float(cost_per_quantity)

        # Calculate extra cost
        extra_cost = quantity * cost_per_quantity
        result = f"Extra Works: {extra_works}, Qty: {quantity} @ ₹{cost_per_quantity} = ₹{extra_cost:.2f}\n{'-'*40}\n"

        # Insert into text display
        text_display.insert(tk.END, result)

        # Update total cost
        update_total()

        # Clear inputs
        entry_extra_works.delete(0, tk.END)
        entry_quantity.delete(0, tk.END)
        entry_cost_per_quantity.delete(0, tk.END)

    except ValueError:
        messagebox.showerror("Input Error", "Please enter valid numerical values.")

def validate_customer_info():
    customer_name = entry_customer_name.get().strip()
    building_site = entry_building_site.get().strip()
    validity_date = entry_validity_date.get().strip()

    if not customer_name:
        messagebox.showerror("Input Error", "Customer name cannot be empty.")
        return False

    if not re.match("^[A-Za-z ]*$", customer_name):
        messagebox.showerror("Input Error", "Customer name should only contain alphabets.")
        entry_customer_name.delete(0, tk.END)
        return False

    if not building_site:
        messagebox.showerror("Input Error", "Building site cannot be empty.")
        return False

    try:
        datetime.strptime(validity_date, "%Y-%m-%d")
    except ValueError:
        messagebox.showerror("Input Error", "Validity date must be in YYYY-MM-DD format.")
        entry_validity_date.delete(0, tk.END)
        return False

    return True

def clear_floor_inputs():
    entry_floor_name.delete(0, tk.END)
    entry_area_sqft.delete(0, tk.END)
    entry_cost_per_sqft.delete(0, tk.END)

def clear_extra_work_inputs():
    entry_extra_works.delete(0, tk.END)
    entry_quantity.delete(0, tk.END)
    entry_cost_per_quantity.delete(0, tk.END)

def clear_all():
    entry_customer_name.delete(0, tk.END)
    entry_building_site.delete(0, tk.END)
    entry_validity_date.delete(0, tk.END)
    entry_floor_name.delete(0, tk.END)
    entry_area_sqft.delete(0, tk.END)
    entry_cost_per_sqft.delete(0, tk.END)
    entry_extra_works.delete(0, tk.END)
    entry_quantity.delete(0, tk.END)
    entry_cost_per_quantity.delete(0, tk.END)
    email_entry.delete(0, tk.END)

    # Clear text display
    text_display.delete("1.0", tk.END)
    total_label.config(text="Total Project Cost: ₹0.00")

def update_total():
    content = text_display.get("1.0", tk.END).strip()
    total_cost = 0

    for line in content.splitlines():
        if "=" in line:
            try:
                cost = float(line.split("=")[-1].strip().replace("₹", "").replace(",", ""))
                total_cost += cost
            except ValueError:
                continue

    total_label.config(text=f"Total Project Cost: ₹{total_cost:.2f}")

def export_to_pdf():
    if not validate_customer_info():
        return

    content = text_display.get("1.0", tk.END).strip()
    if not content:
        messagebox.showwarning("Export Error", "No data to export!")
        return

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    def safe_text(text):
        """ Normalize text to remove unsupported characters for PDF compatibility """
        return unicodedata.normalize('NFKD', text).encode('latin-1', 'ignore').decode('latin-1')

    # 🏠 **Header Section**
    pdf.set_font("Arial", style="B", size=16)
    pdf.cell(200, 10, txt=safe_text("Niranjana Construction"), ln=True, align="C")
    
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=safe_text(f"Date: {date.today().strftime('%Y-%m-%d')}"), ln=True, align="C")
    pdf.cell(200, 10, txt=safe_text("Email: viswa26073@gmail.com"), ln=True, align="C")
    pdf.cell(200, 10, txt=safe_text("Phone: 9150447236"), ln=True, align="C")
    pdf.ln(10)  # Add blank line

    # 🧑 **Customer Information**
    pdf.set_font("Arial", style="B", size=12)
    pdf.cell(200, 10, txt=safe_text("Customer Information"), ln=True)
    pdf.set_font("Arial", size=10)
    pdf.cell(60, 10, safe_text("Customer Name:"), border=0)
    pdf.cell(140, 10, safe_text(entry_customer_name.get()), border=0)
    pdf.ln()
    pdf.cell(60, 10, safe_text("Building Site:"), border=0)
    pdf.cell(140, 10, safe_text(entry_building_site.get()), border=0)
    pdf.ln()
    pdf.cell(60, 10, safe_text("Validity Date:"), border=0)
    pdf.cell(140, 10, safe_text(entry_validity_date.get()), border=0)
    pdf.ln(10)  # Add blank line

    # 🏢 **Floor Details Table**
    pdf.set_font("Arial", style="B", size=12)
    pdf.cell(200, 10, txt=safe_text("Floor Details"), ln=True)
    pdf.set_font("Arial", size=10)
    pdf.cell(60, 10, safe_text("Floor Name"), border=1, align="C")
    pdf.cell(40, 10, safe_text("Area (sqft)"), border=1, align="C")
    pdf.cell(40, 10, safe_text("Cost/Unit (INR)"), border=1, align="C")
    pdf.cell(40, 10, safe_text("Total Cost (INR)"), border=1, align="C")
    pdf.ln()

    # **Initialize total project cost**
    total_cost = 0

    # **Extract & Add Floor Data**
    for line in content.splitlines():
        if "Floor Name:" in line:
            try:
                # Extract values correctly
                parts = re.search(r"Floor Name: (.*?), (.*?) sqft X ₹(.*?) = ₹(.*?)$", line)
                if parts:
                    floor_name = parts.group(1).strip()
                    area_sqft = parts.group(2).strip()
                    cost_per_sqft = parts.group(3).strip()
                    floor_total_cost = float(parts.group(4).replace(",", ""))  # Remove commas for float conversion
                    
                    total_cost += floor_total_cost  # Add to total project cost

                    pdf.cell(60, 10, safe_text(floor_name), border=1)
                    pdf.cell(40, 10, safe_text(area_sqft), border=1)
                    pdf.cell(40, 10, safe_text(cost_per_sqft), border=1)
                    pdf.cell(40, 10, safe_text(f"₹{floor_total_cost:.2f}"), border=1)
                    pdf.ln()

            except Exception as e:
                print(f"Error processing floor data: {line} - {e}")

    # 🔧 **Extra Works Table**
    pdf.set_font("Arial", style="B", size=12)
    pdf.cell(200, 10, txt=safe_text("Extra Works Details"), ln=True)
    pdf.set_font("Arial", size=10)
    pdf.cell(60, 10, safe_text("Extra Work"), border=1, align="C")
    pdf.cell(40, 10, safe_text("Quantity"), border=1, align="C")
    pdf.cell(40, 10, safe_text("Cost/Unit (INR)"), border=1, align="C")
    pdf.cell(40, 10, safe_text("Total Cost (INR)"), border=1, align="C")
    pdf.ln()

    # **Extract & Add Extra Work Data**
    for line in content.splitlines():
        if "Extra Works:" in line:
            try:
                # Extract values correctly
                parts = re.search(r"Extra Works: (.*?), Qty: (.*?) @ ₹(.*?) = ₹(.*?)$", line)
                if parts:
                    work_name = parts.group(1).strip()
                    quantity = parts.group(2).strip()
                    cost_per_unit = parts.group(3).strip()
                    extra_total_cost = float(parts.group(4).replace(",", ""))  # Remove commas
                    
                    total_cost += extra_total_cost  # Add to total project cost

                    pdf.cell(60, 10, safe_text(work_name), border=1)
                    pdf.cell(40, 10, safe_text(quantity), border=1)
                    pdf.cell(40, 10, safe_text(cost_per_unit), border=1)
                    pdf.cell(40, 10, safe_text(f"₹{extra_total_cost:.2f}"), border=1)
                    pdf.ln()

            except Exception as e:
                print(f"Error processing extra works data: {line} - {e}")

    # 📊 **Total Project Cost**
    pdf.set_font("Arial", style="B", size=12)
    pdf.cell(200, 10, txt=safe_text(f"Total Project Cost: ₹{total_cost:.2f}"), ln=True, align="C")

    # 📄 **Add Note**
    note = ("Note:\n"
            "1. If the Construction materials rate increases more than 5%, client should bear the extra costs.\n"
            "2. If any work to be done which is not mentioned in the quotation, client should bear the cost for that.\n"
            "3. Client should bear the Cost for EB main board works & all the government formalities.\n"
            "4. EB bill is to be paid by the client during the period of construction.\n"
            "5. Construction water is to be provided by the client if bore water is not available.")
    
    pdf.ln(10)
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 10, txt=safe_text(note))

    # 📝 **Save PDF**
    pdf_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")])
    if pdf_path:
        pdf.output(pdf_path)
        messagebox.showinfo("Export Success", f"The quotation has been exported to {pdf_path}.")
        clear_all()  # Clear all fields after exporting
 
def is_valid_email(email):
    """ Check if email format is valid """
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return re.match(pattern, email) 
      
def send_email():
    if not validate_customer_info():
        return

    content = text_display.get("1.0", tk.END).strip()
    if content:
        email_address = email_entry.get()
        if not email_address:
            messagebox.showerror("Input Error", "Please enter an email address.")
            return

        # Save PDF first
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)

        def safe_text(text):
            return unicodedata.normalize('NFKD', text).encode('latin-1', 'ignore').decode('latin-1')

        # Add header
        pdf.set_font("Arial", style="B", size=14)
        pdf.cell(200, 10, txt=safe_text("Niranjana Construction"), ln=True, align="C")
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt=safe_text(f"Date: {date.today().strftime('%Y-%m-%d')}"), ln=True, align="C")
        pdf.cell(200, 10, txt=safe_text("email: viswa26073@gmail.com"), ln=True, align="C")
        pdf.cell(200, 10, txt=safe_text("Phone: 9150447236"), ln=True, align="C")
        pdf.ln(10)  # Add a blank line

        # Add customer info
        pdf.set_font("Arial", style="B", size=12)
        pdf.cell(200, 10, txt=safe_text("Customer Information"), ln=True)
        pdf.set_font("Arial", size=10)
        pdf.cell(60, 10, safe_text("Customer Name:"), border=0)
        pdf.cell(140, 10, safe_text(entry_customer_name.get()), border=0)
        pdf.ln()
        pdf.cell(60, 10, safe_text("Building Site:"), border=0)
        pdf.cell(140, 10, safe_text(entry_building_site.get()), border=0)
        pdf.ln()
        pdf.cell(60, 10, safe_text("Validity Date:"), border=0)
        pdf.cell(140, 10, safe_text(entry_validity_date.get()), border=0)
        pdf.ln(10)  # Add a blank line

        # Add floor details table
        pdf.set_font("Arial", style="B", size=12)
        pdf.cell(200, 10, txt=safe_text("Floor Details"), ln=True)
        pdf.set_font("Arial", size=10)
        pdf.cell(60, 10, safe_text("Floor Name"), border=1, align="C")
        pdf.cell(40, 10, safe_text("Area (sqft)"), border=1, align="C")
        pdf.cell(40, 10, safe_text("Cost/Unit (INR)"), border=1, align="C")
        pdf.cell(40, 10, safe_text("Total Cost (INR)"), border=1, align="C")
        pdf.ln()

        # Initialize total project cost
        total_cost = 0

        # Process floor data
        for line in content.splitlines():
            if "Floor Name:" in line:
                try:
                    parts = re.search(r"Floor Name: (.*?), (.*?) sqft X ₹(.*?) = ₹(.*?)$", line)
                    if parts:
                        floor_name = parts.group(1).strip()
                        area_sqft = parts.group(2).strip()
                        cost_per_sqft = parts.group(3).strip()
                        floor_total_cost = float(parts.group(4).replace(",", ""))  # Remove commas for float conversion

                        total_cost += floor_total_cost  # Add to total project cost

                        pdf.cell(60, 10, safe_text(floor_name), border=1)
                        pdf.cell(40, 10, safe_text(area_sqft), border=1)
                        pdf.cell(40, 10, safe_text(cost_per_sqft), border=1)
                        pdf.cell(40, 10, safe_text(f"₹{floor_total_cost:.2f}"), border=1)
                        pdf.ln()
                except IndexError:
                    continue

        # Add extra works table
        pdf.set_font("Arial", style="B", size=12)
        pdf.cell(200, 10, txt=safe_text("Extra Works Details"), ln=True)
        pdf.set_font("Arial", size=10)
        pdf.cell(60, 10, safe_text("Extra Work"), border=1, align="C")
        pdf.cell(40, 10, safe_text("Quantity"), border=1, align="C")
        pdf.cell(40, 10, safe_text("Cost/Unit (INR)"), border=1, align="C")
        pdf.cell(40, 10, safe_text("Total Cost (INR)"), border=1, align="C")
        pdf.ln()

        # Process extra works data
        for line in content.splitlines():
            if "Extra Works:" in line:
                try:
                    parts = re.search(r"Extra Works: (.*?), Qty: (.*?) @ ₹(.*?) = ₹(.*?)$", line)
                    if parts:
                        work_name = parts.group(1).strip()
                        quantity = parts.group(2).strip()
                        cost_per_unit = parts.group(3).strip()
                        extra_total_cost = float(parts.group(4).replace(",", ""))  # Remove commas

                        total_cost += extra_total_cost  # Add to total project cost

                        pdf.cell(60, 10, safe_text(work_name), border=1)
                        pdf.cell(40, 10, safe_text(quantity), border=1)
                        pdf.cell(40, 10, safe_text(cost_per_unit), border=1)
                        pdf.cell(40, 10, safe_text(f"₹{extra_total_cost:.2f}"), border=1)
                        pdf.ln()
                except (IndexError, ValueError) as e:
                    print(f"Error processing line: {line}. Error: {e}")
                    continue

        # Add total project cost
        pdf.set_font("Arial", style="B", size=12)
        pdf.cell(200, 10, txt=safe_text(f"Total Project Cost: ₹{total_cost:.2f}"), ln=True, align="C")

        # 📄 **Add Note**
        note = ("Note:\n"
                "1. If the Construction materials rate increases more than 5%, client should bear the extra costs.\n"
                "2. If any work to be done which is not mentioned in the quotation, client should bear the cost for that.\n"
                "3. Client should bear the Cost for EB main board works & all the government formalities.\n"
                "4. EB bill is to be paid by the client during the period of construction.\n"
                "5. Construction water is to be provided by the client if bore water is not available.")
        
        pdf.ln(10)
        pdf.set_font("Arial", size=10)
        pdf.multi_cell(0, 10, txt=safe_text(note))

        # Save the PDF to a temporary file
        pdf_path = "quotation.pdf"
        pdf.output(pdf_path)

        # Email setup
        try:
            sender_email = "2399059@saec.ac.in"  # Replace with your email
            sender_password = "viswavizz26"  # Replace with your email password
            subject = "Construction Quotation"

            # Create email
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = email_address
            msg['Subject'] = subject

            body = "Please find the attached quotation for the construction project."
            msg.attach(MIMEText(body, 'plain'))

            # Attach PDF
            attachment = open(pdf_path, "rb")
            part = MIMEBase('application', 'octet-stream')
            part.set_payload((attachment).read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f"attachment; filename={pdf_path}")
            msg.attach(part)

            # Send email
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(sender_email, sender_password)
            text = msg.as_string()
            server.sendmail(sender_email, email_address, text)
            server.quit()

            messagebox.showinfo("Email Sent", f"The quotation has been sent to {email_address}.")
        except Exception as e:
            messagebox.showerror("Email Error", f"An error occurred while sending the email: {e}")
    else:
        messagebox.showwarning("Email Error", "No data to send!")
        
# Splash Screen
splash_root = tk.Tk()
splash_root.title("Splash Screen")
splash_root.configure(bg='grey')

# Make the splash screen a fixed size
splash_width = 800
splash_height = 400
screen_width = splash_root.winfo_screenwidth()
screen_height = splash_root.winfo_screenheight()
x = (screen_width / 2) - (splash_width / 2)
y = (screen_height / 2) - (splash_height / 2)
splash_root.geometry(f"{splash_width}x{splash_height}+{int(x)}+{int(y)}")

# Center the splash label
splash_label = tk.Label(splash_root, text="CONSTRUCTION ESTIMATOR", font=("Arial", 40), bg='grey', fg='white')
splash_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

# Close the splash screen after 3 seconds
splash_root.after(3000, splash_root.destroy)

# Run the splash screen
splash_root.mainloop()


# GUI Setup
root = tk.Tk()
root.title("Construction Quotation Generator")
root.configure(bg='grey')

# **Make Window Fullscreen**
root.state('zoomed')

# **Configure root grid to expand properly**
root.grid_rowconfigure(0, weight=1)
root.grid_columnconfigure(0, weight=1)
root.grid_columnconfigure(1, weight=3)

# Common Font for Dynamic Sizing
FONT = ("Arial", 16)
BUTTON_FONT = ("Arial", 14, "bold")
SMALL_BUTTON_FONT = ("Arial", 12, "bold")  # Smaller Buttons

# **Left frame (Inputs)**
left_frame = tk.Frame(root, bg='grey')
left_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsw")
left_frame.grid_rowconfigure(100, weight=1)  # Ensure stretching

# **Reusable Label-Entry Function**
def create_label_entry(parent, text, row):
    tk.Label(parent, text=text, bg='grey', fg='white', font=FONT).grid(row=row, column=0, padx=10, pady=5, sticky="w")
    entry = tk.Entry(parent, font=FONT, width=20)
    entry.grid(row=row, column=1, padx=10, pady=5, sticky="w")
    return entry

# **Customer Information**
entry_customer_name = create_label_entry(left_frame, "Customer Name:", 0)
entry_building_site = create_label_entry(left_frame, "Building Site:", 1)

# **Validity Date (Fixed visibility)**
tk.Label(left_frame, text="Validity Date:", bg='grey', fg='white', font=FONT).grid(row=2, column=0, padx=10, pady=5, sticky="w")
entry_validity_date = DateEntry(left_frame, font=FONT, date_pattern='yyyy-mm-dd')
entry_validity_date.grid(row=2, column=1, padx=10, pady=5, sticky="w")

email_entry = create_label_entry(left_frame, "Email:", 3)

# **Separator**
ttk.Separator(left_frame, orient='horizontal').grid(row=4, column=0, columnspan=2, pady=10, sticky="ew")

# **Floor Inputs**
tk.Label(left_frame, text="🏢 Floor Information", bg='grey', fg='white', font=("Arial", 18, "bold")).grid(row=5, column=0, columnspan=2, pady=5, sticky="w")
entry_floor_name = create_label_entry(left_frame, "Floor Name:", 6)
entry_area_sqft = create_label_entry(left_frame, "Area (sqft):", 7)
entry_cost_per_sqft = create_label_entry(left_frame, "Cost per sqft (INR):", 8)

tk.Button(left_frame, text="Add Floor Info", command=add_floor_info, bg='#4A90E2', fg='white', font=SMALL_BUTTON_FONT).grid(row=9, column=0, columnspan=2, pady=5, sticky="ew")

# **Separator**
ttk.Separator(left_frame, orient='horizontal').grid(row=10, column=0, columnspan=2, pady=10, sticky="ew")

# **Extra Works Inputs**
tk.Label(left_frame, text="🛠️ Extra Works", bg='grey', fg='white', font=("Arial", 18, "bold")).grid(row=11, column=0, columnspan=2, pady=5, sticky="w")
entry_extra_works = create_label_entry(left_frame, "Extra Works:", 12)
entry_quantity = create_label_entry(left_frame, "Quantity:", 13)
entry_cost_per_quantity = create_label_entry(left_frame, "Cost per Quantity (INR):", 14)

tk.Button(left_frame, text="Add Extra Work Info", command=add_extra_work_info, bg='#4A90E2', fg='white', font=SMALL_BUTTON_FONT).grid(row=15, column=0, columnspan=2, pady=5, sticky="ew")

# **Separator**
ttk.Separator(left_frame, orient='horizontal').grid(row=16, column=0, columnspan=2, pady=10, sticky="ew")

# **Fetch Previous Quotations**
tk.Label(left_frame, text="📜 Fetch Previous Quotation", bg='grey', fg='white', font=("Arial", 18, "bold")).grid(row=17, column=0, columnspan=2, pady=5, sticky="w")
fetch_email_entry = create_label_entry(left_frame, "Email:", 18)

tk.Button(left_frame, text="View Previous Quotation", command=fetch_quotation, bg='#FFD700', fg='black', font=SMALL_BUTTON_FONT).grid(row=19, column=0, columnspan=2, pady=5, sticky="ew")

# **Right frame (Display & Actions)**
right_frame = tk.Frame(root, bg='grey')
right_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
right_frame.grid_rowconfigure(0, weight=1)  # Expand text display
right_frame.grid_columnconfigure(0, weight=1)  # Expand buttons

# **Text Display**
text_display = tk.Text(right_frame, font=FONT, wrap="word")
text_display.grid(row=0, column=0, columnspan=4, padx=10, pady=10, sticky="nsew")

# **Total Cost Label**
total_label = tk.Label(right_frame, text="Total Project Cost: ₹0.00", bg='grey', fg='white', font=("Arial", 18, "bold"))
total_label.grid(row=1, column=0, columnspan=4, pady=10, sticky="ew")

# **Buttons in Right Frame**
button_frame = tk.Frame(right_frame, bg='grey')
button_frame.grid(row=2, column=0, columnspan=4, pady=10, sticky="ew")
button_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)  # Make buttons stretch

buttons = [
    ("Export to PDF", export_to_pdf, '#4A90E2'),
    ("Send Email", send_email, '#90EE90'),
    ("Save Quotation", save_quotation, '#4A90E2'),
    ("Clear", clear_all, '#FF6347'),
]

for i, (text, command, color) in enumerate(buttons):
    tk.Button(button_frame, text=text, command=command, bg=color, fg='white', font=BUTTON_FONT).grid(row=0, column=i, padx=10, pady=5, sticky="ew")

root.mainloop()