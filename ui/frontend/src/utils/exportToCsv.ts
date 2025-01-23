export const exportToCsv = (filename: string, rows: any[]) => {
    if (!rows || rows.length === 0) {
      console.warn("No data to export");
      return;
    }
  
    const csvContent = [
      Object.keys(rows[0]).join(","), // Headers
      ...rows.map((row) =>
        Object.values(row)
          .map((value) => `"${value}"`) // Escape double quotes for CSV
          .join(",")
      ),
    ].join("\n");
  
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const link = document.createElement("a");
    const url = URL.createObjectURL(blob);
    link.href = url;
    link.setAttribute("download", filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };
  