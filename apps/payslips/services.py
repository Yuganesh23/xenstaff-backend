import io
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from apps.common.utils import format_inr

def generate_payslip_pdf(payslip):
    """
    Renders an authenticated, production-grade PDF payslip document.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    story = []
    styles = getSampleStyleSheet()

    # Custom typography styles
    title_style = ParagraphStyle(
        'OrgTitle',
        parent=styles['Heading1'],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#0F172A'),
        alignment=1 # Center
    )
    subtitle_style = ParagraphStyle(
        'OrgSubtitle',
        parent=styles['Normal'],
        fontSize=11,
        leading=14,
        textColor=colors.HexColor('#475569'),
        alignment=1
    )
    section_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading3'],
        fontSize=12,
        leading=15,
        textColor=colors.HexColor('#1E293B'),
        spaceAfter=6
    )
    cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#334155')
    )
    cell_bold_style = ParagraphStyle(
        'TableCellBold',
        parent=styles['Normal'],
        fontSize=9,
        leading=12,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#0F172A')
    )

    item = payslip.payroll_item
    emp = item.employee
    run = item.payroll_run
    org = payslip.organization

    # 1. Header
    story.append(Paragraph(org.legal_name or org.name, title_style))
    story.append(Paragraph(f"PAYSLIP FOR {run.month:02d}/{run.year} — {payslip.payslip_number}", subtitle_style))
    story.append(Spacer(1, 15))

    # 2. Employee Details Grid
    emp_details = [
        [
            Paragraph("<b>Employee Code:</b>", cell_style), Paragraph(emp.employee_code, cell_style),
            Paragraph("<b>Employee Name:</b>", cell_style), Paragraph(emp.full_name, cell_bold_style)
        ],
        [
            Paragraph("<b>Department:</b>", cell_style), Paragraph(emp.department.name, cell_style),
            Paragraph("<b>Designation:</b>", cell_style), Paragraph(emp.designation, cell_style)
        ],
        [
            Paragraph("<b>Branch:</b>", cell_style), Paragraph(emp.branch.name, cell_style),
            Paragraph("<b>Joining Date:</b>", cell_style), Paragraph(str(emp.joining_date), cell_style)
        ],
        [
            Paragraph("<b>Bank Name:</b>", cell_style), Paragraph(emp.bank_name or "N/A", cell_style),
            Paragraph("<b>Bank A/C No:</b>", cell_style), Paragraph(f"••••{emp.bank_account_number[-4:]}" if emp.bank_account_number else "N/A", cell_style)
        ],
        [
            Paragraph("<b>Calendar Days:</b>", cell_style), Paragraph(str(item.calendar_days), cell_style),
            Paragraph("<b>Payable Days:</b>", cell_style), Paragraph(f"{item.payable_days} (LOP: {item.lop_days})", cell_bold_style)
        ]
    ]

    t_details = Table(emp_details, colWidths=[90, 180, 90, 180])
    t_details.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F8FAFC')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(t_details)
    story.append(Spacer(1, 15))

    # 3. Earnings & Deductions Tables
    earnings_lines = item.lines.filter(component_type='EARNING')
    deductions_lines = item.lines.filter(component_type='DEDUCTION')

    max_rows = max(len(earnings_lines), len(deductions_lines), 1)
    table_data = [
        [
            Paragraph("<b>EARNINGS</b>", cell_bold_style), Paragraph("<b>AMOUNT</b>", cell_bold_style),
            Paragraph("<b>DEDUCTIONS</b>", cell_bold_style), Paragraph("<b>AMOUNT</b>", cell_bold_style)
        ]
    ]

    for i in range(max_rows):
        earn_col1 = earnings_lines[i].component_name if i < len(earnings_lines) else ""
        earn_col2 = format_inr(earnings_lines[i].calculated_amount) if i < len(earnings_lines) else ""

        ded_col1 = deductions_lines[i].component_name if i < len(deductions_lines) else ""
        ded_col2 = format_inr(deductions_lines[i].calculated_amount) if i < len(deductions_lines) else ""

        table_data.append([
            Paragraph(earn_col1, cell_style), Paragraph(earn_col2, cell_style),
            Paragraph(ded_col1, cell_style), Paragraph(ded_col2, cell_style)
        ])

    # Totals row
    table_data.append([
        Paragraph("<b>Total Gross Earnings</b>", cell_bold_style), Paragraph(f"<b>{format_inr(item.gross_earnings)}</b>", cell_bold_style),
        Paragraph("<b>Total Deductions</b>", cell_bold_style), Paragraph(f"<b>{format_inr(item.total_deductions)}</b>", cell_bold_style)
    ])

    salary_table = Table(table_data, colWidths=[180, 90, 180, 90])
    salary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (1, 0), colors.HexColor('#E0F2FE')),
        ('BACKGROUND', (2, 0), (3, 0), colors.HexColor('#FEE2E2')),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#F1F5F9')),
        ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor('#94A3B8')),
        ('LINEABOVE', (0, -1), (-1, -1), 1, colors.HexColor('#94A3B8')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(salary_table)
    story.append(Spacer(1, 15))

    # 4. Net Salary Block
    net_data = [
        [
            Paragraph("<b>NET PAYABLE AMOUNT:</b>", section_style),
            Paragraph(f"<font size=14 color='#047857'><b>{format_inr(item.net_salary)}</b></font>", section_style)
        ]
    ]
    net_table = Table(net_data, colWidths=[200, 340])
    net_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#ECFDF5')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#10B981')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(net_table)
    story.append(Spacer(1, 20))

    # 5. Footer Notice
    footer_text = Paragraph(
        "<i>Note: This is a system-generated payslip issued by XenStaff HRMS and does not require a physical signature.</i>",
        subtitle_style
    )
    story.append(footer_text)

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
