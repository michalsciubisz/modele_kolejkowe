import tkinter as tk
from tkinter import filedialog, ttk
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import json
import os

# Use TkAgg backend for embedding matplotlib plots in tkinter
matplotlib.use("TkAgg")


# Function to choose file and display data
def open_file():
    # Open file dialog
    file_path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])

    if file_path.endswith(".csv"):
        display_csv(file_path)  # Display CSV data on chart

        # Find corresponding JSON file (assuming it has the same name)
        json_file = file_path.replace(".csv", ".json")
        if os.path.exists(json_file):
            display_json(json_file,
                         os.path.basename(file_path))  # Display JSON data and use the filename to fetch parameter data


# Function to display CSV data on a chart embedded in tkinter
def display_csv(file_path):
    try:
        # Read CSV data, specifying the semicolon as the delimiter
        df = pd.read_csv(file_path, delimiter=';')

        # Check if there are at least two columns
        if len(df.columns) < 2:
            raise ValueError("The CSV file must have at least two columns for plotting.")

        # Create a new figure
        fig, ax = plt.subplots(figsize=(8, 7.5))
        ax.plot(df[df.columns[1]], df[df.columns[0]], marker='o')
        ax.set_title(f"Data from {os.path.basename(file_path)}")
        ax.set_xlabel(df.columns[1])
        ax.set_ylabel(df.columns[0])
        ax.grid(True)

        # Embed the figure in the tkinter window
        canvas = FigureCanvasTkAgg(fig, master=plot_frame)  # Create canvas for figure
        canvas.draw()
        canvas.get_tk_widget().grid(row=0, column=0, sticky='nsew')  # Display the canvas in grid

    except Exception as e:
        # If an error occurs, display it as a messagebox
        tk.messagebox.showerror("Error", f"Failed to plot CSV data: {str(e)}")


# Function to display JSON data, including consultants in a collapsible format
def display_json(json_file, filename_without_extension):
    with open(json_file, 'r') as f:
        json_data = json.load(f)

    # Fetch additional info from ../parameters.json based on the file name
    parameters_path = "parameters.json"
    additional_info = {}
    if os.path.exists(parameters_path):
        with open(parameters_path, 'r') as f_params:
            parameters = json.load(f_params)
            # Use the file name (without extension) to fetch the relevant entry
            name = os.path.splitext(filename_without_extension)[0]
            if name in parameters:
                additional_info = parameters[name]  # Get corresponding data from parameters.json

    # Merge the additional info into the json_data
    json_data['additional_info'] = additional_info

    # Clear the frame first
    for widget in text_frame.winfo_children():
        widget.destroy()

    # Use ttk.Treeview for displaying all data (including additional info and consultants)
    tree = ttk.Treeview(text_frame)
    tree.pack(fill='both', expand=True, padx=10, pady=5)

    # Simulation info from parameters.json
    if "additional_info" in json_data and json_data["additional_info"]:
        additional_info_node = tree.insert("", "end", text="Simulation parameters", open=True)
        for key, value in json_data["additional_info"].items():
            tree.insert(additional_info_node, "end", text=f"{key}: {value}")

    # Add root nodes for general data and consultants
    general_info_node = tree.insert("", "end", text="Simulation results", open=True)

    # Loop through general data and add to the tree
    for key, value in json_data.items():
        if key != "consultants" and key != "additional_info":
            tree.insert(general_info_node, "end", text=f"{key}: {value}")

    # Consultants
    if "consultants" in json_data:
        consultants_node = tree.insert("", "end", text="Consultants results", open=True)
        for i, consultant in enumerate(json_data["consultants"], start=1):
            consultant_name = f"Consultant-{i}"
            consultant_node = tree.insert(consultants_node, "end", text=consultant_name, open=False)

            # Add consultant details as child nodes
            tree.insert(consultant_node, "end", text=f"Handled Calls: {consultant.get('handled_calls', 'N/A')}")
            tree.insert(consultant_node, "end",
                        text=f"Time on Calls: {consultant.get('time_on_calls', 'N/A'):.2f} units")
            tree.insert(consultant_node, "end", text=f"Time on Breaks: {consultant.get('time_on_breaks', 'N/A')} units")


# Main window setup
root = tk.Tk()
root.title("Data Visualizer")
root.geometry("1200x850")  # Adjusted width for side-by-side view

# Create a grid layout with two columns: one for JSON data and one for the plot
root.grid_columnconfigure(0, weight=1)  # Left column for JSON
root.grid_columnconfigure(1, weight=1)  # Right column for chart

# Add buttons
btn_frame = ttk.Frame(root)
btn_frame.grid(row=0, column=0, columnspan=2, pady=10)

open_btn = ttk.Button(btn_frame, text="Open File", command=open_file)
open_btn.pack()

# Frame for displaying JSON data (left side)
text_frame = ttk.Frame(root)
text_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

# Frame for displaying plots (right side)
plot_frame = ttk.Frame(root)
plot_frame.grid(row=1, column=1, sticky="nsew", padx=10, pady=10)

# Run the Tkinter loop
root.mainloop()
