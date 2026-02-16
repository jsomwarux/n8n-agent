# n8n Expression Syntax Cheat Sheet

## Accessing Data
| Expression | What it does |
|-----------|-------------|
| `{{ $json.fieldName }}` | Current item's field |
| `{{ $json['field name'] }}` | Field with spaces |
| `{{ $json.nested.deep.value }}` | Nested field |
| `{{ $('Node Name').item.json.field }}` | Field from a specific node |
| `{{ $('Node Name').all() }}` | All items from a node |
| `{{ $('Node Name').first().json.field }}` | First item from a node |

## Variables
| Variable | What it is |
|----------|-----------|
| `{{ $now }}` | Current datetime |
| `{{ $today }}` | Today's date |
| `{{ $itemIndex }}` | Current item's index (0-based) |
| `{{ $input.all() }}` | All input items |
| `{{ $input.first() }}` | First input item |
| `{{ $execution.id }}` | Current execution ID |
| `{{ $workflow.id }}` | Current workflow ID |

## Conditions
| Expression | What it does |
|-----------|-------------|
| `{{ $if($json.score > 80, "high", "low") }}` | Ternary condition |
| `{{ $json.items ? $json.items.length : 0 }}` | Safe length check (ternary) |

## Common Mistakes
- WRONG: `{{ $json.fieldName?.nested }}` (optional chaining is NOT supported in n8n expressions)
- RIGHT: `{{ $json.fieldName ? $json.fieldName.nested : 'fallback' }}` (use ternary instead)
- WRONG: `{{ $json[fieldName] }}` (missing quotes)
- RIGHT: `{{ $json['fieldName'] }}` or `{{ $json.fieldName }}`
- WRONG: Using `$node["Name"]` (outdated syntax)
- RIGHT: Using `$('Name')` (current syntax)
- WRONG: `{{ $json.content[0].text }}` in expression fields for nested arrays
- RIGHT: Use a Code node for complex data extraction, then reference the output
