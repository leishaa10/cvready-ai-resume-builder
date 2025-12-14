import streamlit as st
import google.generativeai as genai
import os
from fpdf import FPDF

MAX_JOBS = 10
MAX_EDUCATION = 5
MAX_PROJECTS = 10

# Pastel colors - soft and readable
PASTEL_COLORS = {
    'primary': '#A8DADC',      # Pastel blue
    'secondary': '#F1FAEE',     # Off white
    'accent': '#E9C46A',        # Pastel yellow
    'success': '#2A9D8F',       # Teal
    'text': '#264653'           # Dark blue-gray for text
}

CUSTOM_CSS = f"""
<style>
.stApp {{
    background: linear-gradient(135deg, {PASTEL_COLORS['secondary']} 0%, {PASTEL_COLORS['primary']} 100%);
}}
.stButton>button {{
    border-radius: 12px; 
    font-weight: 600; 
    background-color: {PASTEL_COLORS['accent']}; 
    color: {PASTEL_COLORS['text']};
    border: 2px solid {PASTEL_COLORS['text']};
    font-size: 16px;
    padding: 12px 24px;
    transition: all 0.3s ease;
}}
.stButton>button:hover {{
    background-color: {PASTEL_COLORS['success']};
    color: white;
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
}}
h1 {{
    color: #000000 !important;
    font-weight: 800;
    font-size: 3rem;
    margin-bottom: 0.5rem;
    text-shadow: 2px 2px 4px rgba(255,255,255,0.8);
}}
h2, h3 {{
    color: #003153;
    font-weight: 700;
}}
.stTabs [data-baseweb="tab-list"] {{
    background-color: rgba(255, 255, 255, 0.9);
    border-radius: 12px;
    padding: 8px;
    gap: 8px;
}}
.stTabs [data-baseweb="tab"] {{
    color: {PASTEL_COLORS['text']};
    font-weight: 600;
    font-size: 16px;
    border-radius: 8px;
    padding: 8px 16px;
}}
.stTabs [aria-selected="true"] {{
    background-color: {PASTEL_COLORS['accent']};
    color: {PASTEL_COLORS['text']};
}}
.stTextInput>div>div>input, .stTextArea>div>div>textarea {{
    border: 2px solid {PASTEL_COLORS['primary']};
    border-radius: 8px;
    font-size: 15px;
    background-color: white;
    color: {PASTEL_COLORS['text']};
}}
.stTextInput>div>div>input:focus, .stTextArea>div>div>textarea:focus {{
    border-color: {PASTEL_COLORS['success']};
    box-shadow: 0 0 0 2px rgba(42, 157, 143, 0.1);
}}
.stTextInput>label, .stTextArea>label, .stNumberInput>label {{
    color: {PASTEL_COLORS['text']};
    font-weight: 600;
    font-size: 16px;
}}
.stExpander {{
    background-color: rgba(255, 255, 255, 0.95);
    border: 2px solid {PASTEL_COLORS['primary']};
    border-radius: 12px;
    margin-bottom: 12px;
}}
.stAlert {{
    border-radius: 10px;
    border-left: 4px solid {PASTEL_COLORS['success']};
}}
div[data-testid="stMarkdownContainer"] p {{
    color: #003153;
    line-height: 1.6;
}}
.generated-resume {{
    background-color: white;
    padding: 2rem;
    border-radius: 12px;
    border: 2px solid {PASTEL_COLORS['primary']};
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    color: {PASTEL_COLORS['text']};
    line-height: 1.8;
    white-space: pre-wrap;
}}
</style>
"""

def generate_resume_with_gemini(resume_data: dict) -> str:
    """Generate resume using Gemini AI"""
    try:
        # Set your Gemini API key
        api_key = 'AIzaSyAMgvnz_bqaRohbLOeyqQSPMEp7f9ONCbw'
        
        # Configure Gemini
        genai.configure(api_key=api_key)
        
        # Build the prompt first
        prompt = build_resume_prompt(resume_data)
        
        # Use the correct model name that works with your API key
        model = genai.GenerativeModel('models/gemini-2.5-flash')
        response = model.generate_content(prompt)
        
        if response and response.text:
            return response.text
        
        return "Error: No response generated"
        
    except Exception as e:
        error_msg = str(e)
        if "API_KEY_INVALID" in error_msg or "API key" in error_msg:
            return "Error: Invalid API key. Please verify your Gemini API key is correct."
        elif "quota" in error_msg.lower() or "429" in error_msg:
            return "Error: API quota exceeded. Please try again later or check your API limits."
        elif "403" in error_msg:
            return "Error: API access forbidden. Your API key may not have Gemini access enabled."
        else:
            return f"Error: {error_msg}"

def build_resume_prompt(resume_data: dict) -> str:
    """Build a comprehensive prompt for resume generation"""
    basic = resume_data.get('basic_info', {})
    experiences = resume_data.get('experience', [])
    education = resume_data.get('education', [])
    projects = resume_data.get('projects', [])
    
    # Format experiences
    exp_text = "\n".join([
        f"Job: {exp['title']} at {exp.get('company', 'N/A')}\n  Period: {exp.get('start', 'N/A')} - {exp.get('end', 'N/A')}\n  Responsibilities: {exp.get('responsibilities', 'N/A')}"
        for exp in experiences if exp.get('title')
    ]) or "No experience provided"
    
    # Format education
    edu_text = "\n".join([
        f"{edu['degree']} from {edu.get('institution', 'N/A')} ({edu.get('year', 'N/A')})"
        for edu in education if edu.get('degree')
    ]) or "No education provided"
    
    # Format projects
    proj_text = "\n".join([
        f"Project: {proj['name']}\n  Description: {proj.get('description', 'N/A')}\n  Technologies: {proj.get('technologies', 'N/A')}"
        for proj in projects if proj.get('name')
    ]) or "No projects provided"
    
    return f"""You are a professional resume writer. Create an enhanced, ATS-friendly resume that showcases the candidate's strengths. 

CRITICAL FORMATTING RULES - FOLLOW EXACTLY:
1. NEVER use asterisks (*) anywhere in the resume
2. Use dashes (-) for ALL bullet points
3. Use UPPERCASE for section headers only
4. Write complete, impactful sentences with action verbs
5. Add quantifiable achievements where possible (percentages, numbers, metrics)
6. Enhance and expand the content professionally - don't just copy the input
7. Make responsibilities more detailed and impressive
8. Keep clean structure for PDF conversion

CANDIDATE INFORMATION:
Name: {basic.get('name', 'N/A')}
Email: {basic.get('email', 'N/A')}
Phone: {basic.get('phone', 'N/A')}
Location: {basic.get('location', 'N/A')}
LinkedIn: {basic.get('linkedin', 'N/A')}
Target Position: {basic.get('job_title', 'N/A')}

PROFESSIONAL SUMMARY (enhance this to be more compelling):
{basic.get('summary', 'N/A')}

SKILLS (organize by category if appropriate):
{basic.get('skills', 'N/A')}

WORK EXPERIENCE (expand each point with impact and results):
{exp_text}

EDUCATION:
{edu_text}

PROJECTS (make these more detailed and impressive):
{proj_text}

---

OUTPUT FORMAT:
Use this exact structure with proper spacing:

[NAME IN CAPS]
[Contact info on one line separated by |]

PROFESSIONAL SUMMARY
[Enhanced 3-4 sentence summary highlighting key strengths and career goals]

SKILLS
[Organized skills, possibly grouped by category]

WORK EXPERIENCE

[JOB TITLE] | [Company Name] | [Dates]
- [Enhanced responsibility with action verb and measurable impact]
- [Another detailed achievement]
- [Add more points if appropriate]

EDUCATION

[DEGREE] | [Institution] | [Year]
- [Any relevant coursework, honors, or GPA if strong]

PROJECTS

[Project Name]
- [Detailed description with technical approach and outcomes]
- [Technologies and methodologies used]
- [Impact or results achieved]

REMEMBER: NO ASTERISKS - Use dashes (-) for bullets. Make content professional and impressive."""

def create_pdf_resume(resume_text: str, candidate_name: str) -> bytes:
    """Create a properly formatted PDF from the resume text"""
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_margins(15, 15, 15)
        
        # Aggressively clean the text - remove ALL asterisks and markdown
        cleaned_text = resume_text.replace('**', '').replace('*', '').replace('•', '-')
        lines = cleaned_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                pdf.ln(3)
                continue
            
            # Detect section headers (all caps lines or common headers)
            if (line.isupper() and len(line) > 3) or any(header in line.upper() for header in ['PROFESSIONAL SUMMARY', 'SKILLS', 'WORK EXPERIENCE', 'EDUCATION', 'PROJECTS']):
                pdf.ln(4)
                pdf.set_font("Arial", 'B', 12)
                pdf.set_text_color(0, 49, 83)  # Prussian blue
                pdf.multi_cell(0, 7, line.encode('latin-1', 'replace').decode('latin-1'))
                pdf.ln(1)
                pdf.set_font("Arial", size=10)
                pdf.set_text_color(0, 0, 0)
            
            # Detect bullet points (lines starting with -)
            elif line.startswith('-'):
                pdf.set_font("Arial", size=10)
                clean_line = line.lstrip('-').strip()
                # Add bullet point
                pdf.cell(3)
                pdf.cell(3, 5, '-')
                pdf.multi_cell(0, 5, clean_line.encode('latin-1', 'replace').decode('latin-1'))
            
            # Detect job titles or emphasis (contains | or all caps words)
            elif '|' in line or any(word.isupper() and len(word) > 2 for word in line.split()):
                pdf.set_font("Arial", 'B', 10)
                pdf.multi_cell(0, 6, line.encode('latin-1', 'replace').decode('latin-1'))
                pdf.set_font("Arial", size=10)
            
            # Regular text
            else:
                pdf.set_font("Arial", size=10)
                pdf.multi_cell(0, 5, line.encode('latin-1', 'replace').decode('latin-1'))
        
        return pdf.output(dest='S').encode('latin-1')
    except Exception as e:
        st.error(f"Error creating PDF: {str(e)}")
        return None

def validate_required_fields(resume_data: dict) -> tuple[bool, str]:
    """Validate that minimum required fields are filled"""
    basic = resume_data.get('basic_info', {})
    
    if not basic.get('name'):
        return False, "Name is required"
    if not basic.get('email'):
        return False, "Email is required"
    if not basic.get('phone'):
        return False, "Phone is required"
    
    # Check if at least some content exists
    has_experience = bool(resume_data.get('experience', []))
    has_education = bool(resume_data.get('education', []))
    has_projects = bool(resume_data.get('projects', []))
    
    if not (has_experience or has_education or has_projects):
        return False, "Please add at least some experience, education, or projects"
    
    return True, ""

# Page config
st.set_page_config(page_title="CVReady - AI Resume Builder", page_icon="📄", layout="wide")
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# Initialize session state
if 'resume_data' not in st.session_state:
    st.session_state.resume_data = {}
if 'generated_resume' not in st.session_state:
    st.session_state.generated_resume = None

# Header
st.title("📄 CVReady")
st.markdown("### <span style='color: #003153;'>AI-Powered Professional Resume Builder</span>", unsafe_allow_html=True)
st.markdown("*Powered by Google Gemini AI*")
st.markdown("---")

# Tabs for organization
tab1, tab2, tab3, tab4 = st.tabs(["📝 Basic Info", "💼 Experience", "🎓 Education & Projects", "✨ Generate Resume"])

# TAB 1: Basic Information
with tab1:
    st.markdown("<h2 style='color: #003153;'>Basic Information</h2>", unsafe_allow_html=True)
    st.markdown("Let's start with your contact details and professional summary.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        name = st.text_input("Full Name *", value=st.session_state.resume_data.get('basic_info', {}).get('name', ''), 
                            placeholder="John Doe")
        email = st.text_input("Email *", value=st.session_state.resume_data.get('basic_info', {}).get('email', ''),
                             placeholder="john.doe@email.com")
        phone = st.text_input("Phone *", value=st.session_state.resume_data.get('basic_info', {}).get('phone', ''),
                             placeholder="+1 (555) 123-4567")
    
    with col2:
        location = st.text_input("Location", value=st.session_state.resume_data.get('basic_info', {}).get('location', ''),
                                placeholder="New York, NY")
        linkedin = st.text_input("LinkedIn URL", value=st.session_state.resume_data.get('basic_info', {}).get('linkedin', ''),
                                placeholder="https://linkedin.com/in/johndoe")
        job_title = st.text_input("Target Job Title", value=st.session_state.resume_data.get('basic_info', {}).get('job_title', ''),
                                  placeholder="Software Engineer")
    
    st.markdown("#### <span style='color: #003153;'>Professional Summary</span>", unsafe_allow_html=True)
    summary = st.text_area("Brief overview of your professional background", 
                          value=st.session_state.resume_data.get('basic_info', {}).get('summary', ''),
                          placeholder="Results-driven professional with 5+ years of experience...", 
                          height=150)
    
    st.markdown("#### <span style='color: #003153;'>Skills</span>", unsafe_allow_html=True)
    skills = st.text_area("List your key skills (comma-separated)", 
                         value=st.session_state.resume_data.get('basic_info', {}).get('skills', ''),
                         placeholder="Python, JavaScript, React, Machine Learning, Data Analysis, SQL", 
                         height=100)
    
    if st.button("💾 Save Basic Info", type="primary", use_container_width=True):
        if not name or not email or not phone:
            st.error("⚠️ Please fill in all required fields (Name, Email, Phone)")
        else:
            st.session_state.resume_data['basic_info'] = {
                'name': name, 'email': email, 'phone': phone, 
                'location': location, 'linkedin': linkedin, 'job_title': job_title,
                'skills': skills, 'summary': summary
            }
            st.success("✅ Basic information saved successfully!")

# TAB 2: Work Experience
with tab2:
    st.markdown("<h2 style='color: #003153;'>Work Experience</h2>", unsafe_allow_html=True)
    st.markdown("Add your professional work history.")
    
    num_jobs = st.number_input("Number of positions", min_value=1, max_value=MAX_JOBS, value=1, key="num_jobs")
    
    experiences = []
    for i in range(num_jobs):
        with st.expander(f"💼 Position #{i+1}", expanded=(i==0)):
            col1, col2 = st.columns(2)
            with col1:
                title = st.text_input("Job Title", key=f"job_title_{i}", placeholder="Software Engineer")
                company = st.text_input("Company", key=f"company_{i}", placeholder="Tech Corp")
            with col2:
                start = st.text_input("Start Date", key=f"start_{i}", placeholder="Jan 2020")
                end = st.text_input("End Date (or 'Present')", key=f"end_{i}", placeholder="Present")
            
            resp = st.text_area("Key Responsibilities & Achievements", 
                              key=f"resp_{i}", 
                              height=120,
                              placeholder="- Led development of...\n- Improved performance by...\n- Collaborated with...")
            
            if title or company:
                experiences.append({
                    'title': title, 
                    'company': company, 
                    'start': start, 
                    'end': end, 
                    'responsibilities': resp
                })
    
    if st.button("💾 Save Work Experience", type="primary", use_container_width=True):
        st.session_state.resume_data['experience'] = experiences
        st.success(f"✅ Saved {len(experiences)} work experience(s)!")

# TAB 3: Education & Projects
with tab3:
    st.markdown("<h2 style='color: #003153;'>Education</h2>", unsafe_allow_html=True)
    
    num_edu = st.number_input("Number of education entries", min_value=1, max_value=MAX_EDUCATION, value=1, key="num_edu")
    
    education = []
    for i in range(num_edu):
        with st.expander(f"🎓 Education #{i+1}", expanded=(i==0)):
            degree = st.text_input("Degree", key=f"degree_{i}", placeholder="Bachelor of Science in Computer Science")
            institution = st.text_input("Institution", key=f"institution_{i}", placeholder="University of Technology")
            year = st.text_input("Graduation Year", key=f"year_{i}", placeholder="2020")
            
            if degree or institution:
                education.append({'degree': degree, 'institution': institution, 'year': year})
    
    st.markdown("---")
    st.markdown("<h2 style='color: #003153;'>Projects</h2>", unsafe_allow_html=True)
    
    num_projects = st.number_input("Number of projects", min_value=0, max_value=MAX_PROJECTS, value=1, key="num_projects")
    
    projects = []
    for i in range(num_projects):
        with st.expander(f"🚀 Project #{i+1}", expanded=(i==0)):
            proj_name = st.text_input("Project Name", key=f"proj_{i}", placeholder="E-commerce Platform")
            proj_desc = st.text_area("Description", key=f"desc_{i}", 
                                    placeholder="Built a full-stack e-commerce application...",
                                    height=100)
            proj_tech = st.text_input("Technologies Used", key=f"tech_{i}", placeholder="React, Node.js, MongoDB")
            
            if proj_name:
                projects.append({'name': proj_name, 'description': proj_desc, 'technologies': proj_tech})
    
    if st.button("💾 Save Education & Projects", type="primary", use_container_width=True):
        st.session_state.resume_data['education'] = education
        st.session_state.resume_data['projects'] = projects
        st.success(f"✅ Saved {len(education)} education(s) and {len(projects)} project(s)!")

# TAB 4: Generate Resume
with tab4:
    st.markdown("<h2 style='color: #003153;'>✨ Generate Your Professional Resume</h2>", unsafe_allow_html=True)
    
    if not st.session_state.resume_data:
        st.warning("⚠️ Please fill in your information in the previous tabs first!")
    else:
        # Validate required fields
        is_valid, error_msg = validate_required_fields(st.session_state.resume_data)
        
        if not is_valid:
            st.error(f"⚠️ {error_msg}")
        else:
            st.success("✅ All required information collected!")
            
            # Show summary of collected data
            basic = st.session_state.resume_data.get('basic_info', {})
            exp_count = len(st.session_state.resume_data.get('experience', []))
            edu_count = len(st.session_state.resume_data.get('education', []))
            proj_count = len(st.session_state.resume_data.get('projects', []))
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("👤 Name", basic.get('name', 'N/A'))
            col2.metric("💼 Experiences", exp_count)
            col3.metric("🎓 Education", edu_count)
            col4.metric("🚀 Projects", proj_count)
            
            st.markdown("---")
            
            if st.button("✨ Generate AI-Powered Resume", type="primary", use_container_width=True, key="generate_btn"):
                with st.spinner("🤖 Gemini AI is crafting your professional resume... This may take a moment."):
                    result = generate_resume_with_gemini(st.session_state.resume_data)
                    st.session_state.generated_resume = result
                    st.rerun()

# Display generated resume
if st.session_state.generated_resume:
    st.markdown("---")
    st.markdown("## 📄 Your Generated Resume")
    
    # Display in a nice container
    st.markdown(f'<div class="generated-resume">{st.session_state.generated_resume}</div>', 
                unsafe_allow_html=True)
    
    # Download buttons
    col1, col2 = st.columns(2)
    
    with col1:
        st.download_button(
            label="📥 Download as Text",
            data=st.session_state.generated_resume,
            file_name=f"{st.session_state.resume_data.get('basic_info', {}).get('name', 'resume').replace(' ', '_')}_resume.txt",
            mime="text/plain",
            type="primary",
            use_container_width=True
        )
    
    with col2:
        # Generate PDF
        candidate_name = st.session_state.resume_data.get('basic_info', {}).get('name', 'resume')
        pdf_data = create_pdf_resume(st.session_state.generated_resume, candidate_name)
        
        if pdf_data:
            st.download_button(
                label="📄 Download as PDF",
                data=pdf_data,
                file_name=f"{candidate_name.replace(' ', '_')}_resume.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True
            )
    
    # Option to regenerate
    if st.button("🔄 Regenerate Resume", use_container_width=False):
        with st.spinner("🤖 Regenerating your resume with Gemini AI..."):
            result = generate_resume_with_gemini(st.session_state.resume_data)
            st.session_state.generated_resume = result
            st.rerun()

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #264653; padding: 20px;'>
        <p><strong>CVReady</strong> - AI-Powered Resume Builder</p>
        <p style='font-size: 14px;'>Powered by Google Gemini AI 🚀</p>
    </div>
    """,
    unsafe_allow_html=True
)