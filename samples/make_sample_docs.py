"""Generate the binary sample resumes (PDF + DOCX) committed under samples/inputs/.

Run once: ``python samples/make_sample_docs.py``. Kept in the repo so the binary inputs
are reproducible and reviewers can see exactly what prose the resume adapter parses.
"""

from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).resolve().parent

JANE_RESUME = [
    "Jane McDonald",
    "jane.mcdonald@example.com | +1 (415) 555-2671 | San Francisco, CA",
    "",
    "Summary",
    "Staff software engineer focused on distributed systems and data platforms.",
    "",
    "Skills",
    "Python, Go, Kubernetes, PostgreSQL, gRPC, Terraform",
    "",
    "Experience",
    "Staff Software Engineer at Acme Corp   Mar 2021 - Present",
    "Senior Engineer at Globex   Jun 2017 - Feb 2021",
    "",
    "Education",
    "MIT - BS Computer Science, 2014",
]

MARCO_RESUME = [
    "Marco Rossi",
    "marco.rossi@example.com | +39 06 1234 5678 | Rome, Italy",
    "",
    "Summary",
    "Backend engineer with a focus on payments and reliability.",
    "",
    "Skills",
    "Java, Spring, Kafka, PostgreSQL, Docker",
    "",
    "Experience",
    "Backend Engineer at FinPay   Jan 2020 - Present",
    "Software Engineer at Telecom Italia   Sep 2016 - Dec 2019",
    "",
    "Education",
    "Sapienza University of Rome - MS Computer Engineering, 2016",
]

# Adversarial resume: every block targets a specific parsing risk (see
# tests/test_resume_adversarial.py). Three jobs in three date formats incl. an ongoing
# role; a Projects section that must NOT be read as Experience; three skill tiers; a GPA
# glued to the degree line; and a References block of OTHER people's contacts.
ALEX_RESUME = [
    "Alex Rivera",
    "alex.rivera@example.com | +1 (415) 555-0182 | Seattle, WA",
    "",
    "Summary",
    "Full-stack engineer; nine years on distributed backends, plus toy C++ systems for fun.",
    "",
    "Skills",
    "Proficient: Python, JavaScript, TypeScript, SQL",
    "Experienced: React, Django, Node.js, Docker, PostgreSQL",
    "Familiar: Rust, Go, Kubernetes, GraphQL, Redis, Terraform",
    "",
    "Experience",
    "Senior Software Engineer at Cloudscale Systems   May 2021 – Current",
    "Built and operated multi-region ingestion services handling billions of events a day.",
    "Software Engineer at Brightline Analytics   July 2016 – March 2019",
    "Owned the reporting pipeline and migrated a monolith to a service-oriented design.",
    "Junior Software Engineer at Harbor Logistics   July 2012 – March 2016",
    "Wrote internal tooling and shipped the first version of the customer dashboard.",
    "",
    "Projects",
    "Chess Engine — a bitboard chess engine written in C++ with alpha-beta search.",
    "Support Chatbot — a retrieval chatbot built in C# over an internal knowledge base.",
    "",
    "Education",
    "Washington State University — BS Computer Science. Cum. GPA: 3.85/4.0. Graduated 2012.",
    "",
    "References",
    "John Doe, john.doe@email.com, +1 (206) 555-0144",
    "Maria Chen, maria.chen@email.com, +1 (206) 555-0177",
]


def write_pdf(lines: list[str], out: Path) -> None:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    c = canvas.Canvas(str(out), pagesize=letter)
    width, height = letter
    y = height - 72
    for line in lines:
        c.setFont("Helvetica-Bold" if line in ("Summary", "Skills", "Experience",
                  "Projects", "Education", "References") else "Helvetica", 11)
        c.drawString(72, y, line)
        y -= 18
    c.save()


def write_docx(lines: list[str], out: Path) -> None:
    import docx

    document = docx.Document()
    for line in lines:
        document.add_paragraph(line)
    document.save(str(out))


def main() -> None:
    write_pdf(JANE_RESUME, HERE / "inputs" / "jane-mcdonald" / "resume.pdf")
    write_docx(MARCO_RESUME, HERE / "inputs" / "marco-rossi" / "resume.docx")
    (HERE / "inputs" / "alex-rivera").mkdir(parents=True, exist_ok=True)
    write_pdf(ALEX_RESUME, HERE / "inputs" / "alex-rivera" / "resume.pdf")
    print("wrote jane-mcdonald/resume.pdf, marco-rossi/resume.docx, alex-rivera/resume.pdf")


if __name__ == "__main__":
    main()
