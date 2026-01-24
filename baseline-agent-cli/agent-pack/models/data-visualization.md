# Data Visualization

## Generating Rich Visualizations

You can include charts, spreadsheets, and diagrams in your responses using special blocks.

### Charts

Use `:::chart` blocks with Chart.js configuration:

```
:::chart
{
  "type": "bar",
  "data": {
    "labels": ["Jan", "Feb", "Mar"],
    "datasets": [{
      "label": "Sales",
      "data": [100, 150, 200]
    }]
  }
}
:::
```

Supported chart types: bar, line, pie, doughnut.

### Spreadsheets

Use `:::spreadsheet` blocks with 2D array data:

```
:::spreadsheet
[
  ["Name", "Age", "City"],
  ["Alice", 30, "New York"],
  ["Bob", 25, "Los Angeles"]
]
:::
```

The first row is treated as a header. Users can sort and filter the data.

### Diagrams

Use `:::diagram` blocks with Mermaid syntax:

```
:::diagram
graph TD
    A[Start] --> B{Decision}
    B -->|Yes| C[Action]
    B -->|No| D[Skip]
:::
```

Supports flowcharts, sequence diagrams, class diagrams, and more.
See https://mermaid.js.org/syntax/ for the full syntax reference.
