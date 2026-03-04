# Glow Index — Client Brief

## Industry
Skincare / Beauty / Consumer Product Analysis

## What They Need
A 4-LLM ensemble n8n workflow that analyzes skincare products on 6 dimensions:
1. Ingredient Efficacy (0-30)
2. Safety Profile (0-20)
3. Value for Money (0-20)
4. Formula Transparency (0-15)
5. Skin Compatibility (0-10)
6. Sensory & Usability (0-5)

Plus 3 modifiers: lifecycle, category heat, price tier.

## Core Question
"Is the consumer the exit liquidity?" — Does the product deliver genuine value, or is the consumer paying for marketing coordination?

## Architecture
- Stage 1: 4 LLMs independently analyze product (same prompt, same schema)
- Stage 2: Each LLM reviews all 4 Stage 1 results and produces refined consensus
- Final score: average of 4 Stage 2 totals (weighted if outlier >15 points)

## Tier System
- S+ (85-100): Best in Class
- S (70-84): Excellent
- A (55-69): Good
- B (35-54): Average
- C (0-34): Skip
