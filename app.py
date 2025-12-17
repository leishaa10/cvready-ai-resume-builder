import streamlit as st
api_key = st.secrets["GEMINI_API_KEY"]
import google.generativeai as genai
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import os
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.lib import colors
from io import BytesIO

# Page configuration
st.set_page_config(
    page_title="CVReady - AI Resume Builder",
    page_icon="📄",
    layout="wide"
)
st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(135deg, #d4f1f4 0%, #b8e6e6 100%);
    }
    [data-testid="stSidebar"] {
        background-color: #e8f5f5;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #f0f9f9;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background-color: #d4a574;
    }
    </style>
    """, unsafe_allow_html=True)

# Firebase initialization
@st.cache_resource
def init_firebase():
    """Initialize Firebase Admin SDK"""
    try:
        firebase_admin.get_app()
    except ValueError:
        # Try to load from Streamlit secrets first
        if "firebase" in st.secrets:
            cred = credentials.Certificate(dict(st.secrets["firebase"]))
        else:
            # Fallback to local file for development
            cred = credentials.Certificate('serviceAccountKey.json')
        
        firebase_admin.initialize_app(cred)
    return firestore.client()

# Initialize Firebase
db = init_firebase()

# Firebase helper functions
def save_resume_to_firebase(db, resume_data, generated_resume, user_email):
    """Save resume to Firestore"""
    try:
        doc_ref = db.collection('resumes').add({
            'user_email': user_email,
            'resume_data': resume_data,
            'generated_resume': generated_resume,
            'created_at': firestore.SERVER_TIMESTAMP
        })
        return doc_ref[1].id
    except Exception as e:
        st.error(f"Error saving to Firebase: {str(e)}")
        return None

def load_user_resumes(db, user_email):
    """Load all resumes for a user"""
    try:
        resumes = []
        docs = db.collection('resumes')\
            .where('user_email', '==', user_email)\
            .order_by('created_at', direction=firestore.Query.DESCENDING)\
            .limit(10)\
            .stream()
        
        for doc in docs:
            resume = doc.to_dict()
            resume['id'] = doc.id
            resumes.append(resume)
        
        return resumes
    except Exception as e:
        st.error(f"Error loading resumes: {str(e)}")
        return []

def delete_resume_from_firebase(db, doc_id):
    """Delete resume from Firestore"""
    try:
        db.collection('resumes').document(doc_id).delete()
        return True
    except Exception as e:
        st.error(f"Error deleting resume: {str(e)}")
        return False

# AI Resume Generation Functions
def build_resume_prompt(resume_data: dict) -> str:
    """Build the prompt for Gemini"""
    basic = resume_data.get('basic_info', {})
    experiences = resume_data.get('experience', [])
    education = resume_data.get('education', [])
    projects = resume_data.get('projects', [])
    
    prompt = f"""Create a professional, ATS-friendly resume for the following candidate:

PERSONAL INFORMATION:
Name: {basic.get('name', 'N/A')}
Email: {basic.get('email', 'N/A')}
Phone: {basic.get('phone', 'N/A')}
Location: {basic.get('location', 'N/A')}
LinkedIn: {basic.get('linkedin', 'N/A')}
Target Job Title: {basic.get('job_title', 'N/A')}

SKILLS:
{basic.get('skills', 'N/A')}

PROFESSIONAL SUMMARY:
{basic.get('summary', 'Generate a compelling 3-4 sentence professional summary')}

WORK EXPERIENCE:"""
    
    for exp in experiences:
        if exp.get('title'):
            prompt += f"\n\n{exp['title']} at {exp.get('company', 'N/A')}"
            prompt += f"\n{exp.get('start', '')} - {exp.get('end', '')}"
            prompt += f"\n{exp.get('responsibilities', '')}"
    
    prompt += "\n\nEDUCATION:"
    for edu in education:
        if edu.get('degree'):
            prompt += f"\n{edu['degree']}, {edu.get('institution', '')}, {edu.get('year', '')}"
    
    if projects and any(p.get('name') for p in projects):
        prompt += "\n\nPROJECTS:"
        for proj in projects:
            if proj.get('name'):
                prompt += f"\n\n{proj['name']}"
                prompt += f"\n{proj.get('description', '')}"
                prompt += f"\nTechnologies: {proj.get('technologies', '')}"
    
    prompt += """

Please create a well-structured, professional resume with:
1. A compelling professional summary (if not provided, create one)
2. Optimized work experience with achievement-focused bullet points
3. Relevant skills section
4. Clean formatting suitable for ATS systems
5. Action verbs and quantifiable results

Format in clean, readable markdown."""
    
    return prompt

def generate_resume_with_gemini(resume_data: dict) -> str:
    """Generate resume using Gemini AI"""
    try:
        # Get API key from secrets or environment variable
        api_key = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY"))
        
        if not api_key:
            return "Error: Gemini API key not found. Please configure it in Streamlit secrets."
        
        # Configure Gemini
        genai.configure(api_key=api_key)
        
        # Build the prompt first
        prompt = build_resume_prompt(resume_data)
        
        # Use the correct model name
        model = genai.GenerativeModel('gemini-1.5-flash')
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

# PDF Generation Function
def create_professional_pdf(resume_data, generated_resume, template_style="modern"):
    """Create a professional PDF resume"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom styles based on template
    if template_style == "modern":
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#2563eb'),
            spaceAfter=6,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#1e40af'),
            spaceAfter=6,
            spaceBefore=12,
            fontName='Helvetica-Bold',
            borderColor=colors.HexColor('#2563eb'),
            borderWidth=2,
            borderPadding=5
        )
        
    elif template_style == "classic":
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=22,
            textColor=colors.black,
            spaceAfter=6,
            alignment=TA_CENTER,
            fontName='Times-Bold'
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=13,
            textColor=colors.black,
            spaceAfter=6,
            spaceBefore=12,
            fontName='Times-Bold',
            borderColor=colors.black,
            borderWidth=1,
            borderPadding=3
        )
        
    elif template_style == "creative":
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=26,
            textColor=colors.HexColor('#7c3aed'),
            spaceAfter=6,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#7c3aed'),
            spaceAfter=6,
            spaceBefore=12,
            fontName='Helvetica-Bold',
            borderColor=colors.HexColor('#a78bfa'),
            borderWidth=2,
            borderPadding=5
        )
        
    else:  # minimal
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=20,
            textColor=colors.HexColor('#374151'),
            spaceAfter=6,
            alignment=TA_LEFT,
            fontName='Helvetica-Bold'
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=12,
            textColor=colors.HexColor('#374151'),
            spaceAfter=6,
            spaceBefore=12,
            fontName='Helvetica-Bold'
        )
    
    contact_style = ParagraphStyle(
        'ContactStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#6b7280'),
        alignment=TA_CENTER,
        spaceAfter=12
    )
    
    body_style = ParagraphStyle(
        'BodyStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.black,
        spaceAfter=6,
        alignment=TA_JUSTIFY
    )
    
    # Get data
    basic = resume_data.get('basic_info', {})
    experiences = resume_data.get('experience', [])
    education = resume_data.get('education', [])
    projects = resume_data.get('projects', [])
    
    # Header - Name
    name = basic.get('name', 'Your Name')
    elements.append(Paragraph(name.upper(), title_style))
    
    # Contact Information
    contact_info = []
    if basic.get('email'):
        contact_info.append(basic['email'])
    if basic.get('phone'):
        contact_info.append(basic['phone'])
    if basic.get('location'):
        contact_info.append(basic['location'])
    if basic.get('linkedin'):
        contact_info.append(basic['linkedin'])
    
    if contact_info:
        elements.append(Paragraph(' | '.join(contact_info), contact_style))
    
    elements.append(Spacer(1, 0.2*inch))
    
    # Professional Summary
    if basic.get('summary'):
        elements.append(Paragraph("PROFESSIONAL SUMMARY", heading_style))
        elements.append(Paragraph(basic['summary'], body_style))
        elements.append(Spacer(1, 0.15*inch))
    
    # Skills
    if basic.get('skills'):
        elements.append(Paragraph("SKILLS", heading_style))
        elements.append(Paragraph(basic['skills'], body_style))
        elements.append(Spacer(1, 0.15*inch))
    
    # Work Experience
    if experiences and any(exp.get('title') for exp in experiences):
        elements.append(Paragraph("WORK EXPERIENCE", heading_style))
        
        for exp in experiences:
            if exp.get('title'):
                job_header = f"<b>{exp['title']}</b> | {exp.get('company', '')}"
                elements.append(Paragraph(job_header, body_style))
                
                duration = f"{exp.get('start', '')} - {exp.get('end', '')}"
                duration_style = ParagraphStyle('Duration', parent=body_style, textColor=colors.HexColor('#6b7280'), fontSize=9)
                elements.append(Paragraph(duration, duration_style))
                
                if exp.get('responsibilities'):
                    resp_lines = exp['responsibilities'].split('\n')
                    for line in resp_lines:
                        if line.strip():
                            elements.append(Paragraph(f"• {line.strip()}", body_style))
                
                elements.append(Spacer(1, 0.1*inch))
    
    # Education
    if education and any(edu.get('degree') for edu in education):
        elements.append(Paragraph("EDUCATION", heading_style))
        
        for edu in education:
            if edu.get('degree'):
                edu_text = f"<b>{edu['degree']}</b> | {edu.get('institution', '')} | {edu.get('year', '')}"
                elements.append(Paragraph(edu_text, body_style))
                elements.append(Spacer(1, 0.05*inch))
    
    # Projects
    if projects and any(proj.get('name') for proj in projects):
        elements.append(Paragraph("PROJECTS", heading_style))
        
        for proj in projects:
            if proj.get('name'):
                proj_header = f"<b>{proj['name']}</b>"
                elements.append(Paragraph(proj_header, body_style))
                
                if proj.get('description'):
                    elements.append(Paragraph(proj['description'], body_style))
                
                if proj.get('technologies'):
                    tech_style = ParagraphStyle('Tech', parent=body_style, textColor=colors.HexColor('#6b7280'), fontSize=9)
                    elements.append(Paragraph(f"<i>Technologies: {proj['technologies']}</i>", tech_style))
                
                elements.append(Spacer(1, 0.1*inch))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

# Initialize session state
if 'resume_data' not in st.session_state:
    st.session_state.resume_data = {}

# Title
st.title("📄 CVReady")
st.markdown("### Your AI-Powered Resume Builder")
st.markdown("*Powered by Google Gemini & Firebase | TechSprint AI Hack '25*")

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    
    # Check if API key is configured in secrets
    try:
        api_key = st.secrets.get("GEMINI_API_KEY", "")
        if api_key:
            st.success("✅ AI Features Enabled")
        else:
            st.warning("⚠️ API Key not configured in secrets")
            st.info("For deployment: Add GEMINI_API_KEY to Streamlit secrets")
            api_key = st.text_input("Enter Gemini API Key (for local testing)", type="password")
    except:
        st.info("💡 Running in local mode")
        api_key = st.text_input("Enter Gemini API Key", type="password")
    
    st.markdown("---")
    
    # User Email
    user_email = st.text_input("Your Email (for saving)", placeholder="user@example.com")
    
    if user_email:
        st.success(f"✅ Logged in as: {user_email}")
        
        # Saved Resumes
        st.markdown("---")
        st.subheader("💾 Your Saved Resumes")
        
        saved_resumes = load_user_resumes(db, user_email)
        
        if saved_resumes:
            for resume in saved_resumes:
                resume_name = resume.get('resume_data', {}).get('basic_info', {}).get('name', 'Untitled')
                
                with st.expander(f"📄 {resume_name}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if st.button("Load", key=f"load_{resume['id']}", use_container_width=True):
                            st.session_state.resume_data = resume['resume_data']
                            st.session_state.generated_resume = resume.get('generated_resume', '')
                            st.success("✅ Resume loaded!")
                            st.rerun()
                    
                    with col2:
                        if st.button("🗑️ Delete", key=f"delete_{resume['id']}", use_container_width=True):
                            if delete_resume_from_firebase(db, resume['id']):
                                st.success("Deleted!")
                                st.rerun()
        else:
            st.info("No saved resumes yet")
    
    st.markdown("---")
    st.markdown("[Get Gemini API Key](https://makersuite.google.com/app/apikey)")

# Create tabs
tab1, tab2, tab3 = st.tabs(["📝 Basic Info", "💼 Experience", "📄 Generate Resume"])

# Tab 1: Basic Information
with tab1:
    st.header("Basic Information")
    
    col1, col2 = st.columns(2)
    
    with col1:
        name = st.text_input("Full Name *", 
            value=st.session_state.resume_data.get('basic_info', {}).get('name', ''))
        email = st.text_input("Email *", 
            value=st.session_state.resume_data.get('basic_info', {}).get('email', ''))
        phone = st.text_input("Phone *", 
            value=st.session_state.resume_data.get('basic_info', {}).get('phone', ''))
    
    with col2:
        location = st.text_input("Location", 
            value=st.session_state.resume_data.get('basic_info', {}).get('location', ''))
        linkedin = st.text_input("LinkedIn URL", 
            value=st.session_state.resume_data.get('basic_info', {}).get('linkedin', ''))
        job_title = st.text_input("Target Job Title", 
            value=st.session_state.resume_data.get('basic_info', {}).get('job_title', ''))
    
    st.markdown("---")
    
    skills = st.text_area(
        "Skills (comma-separated) *",
        value=st.session_state.resume_data.get('basic_info', {}).get('skills', ''),
        placeholder="Python, Machine Learning, Data Analysis, SQL, TensorFlow",
        height=100
    )
    
    professional_summary = st.text_area(
        "Professional Summary (optional - AI can generate)",
        value=st.session_state.resume_data.get('basic_info', {}).get('summary', ''),
        placeholder="A brief overview of your professional background...",
        height=150
    )
    
    if st.button("💾 Save Basic Info", type="primary"):
        st.session_state.resume_data['basic_info'] = {
            'name': name,
            'email': email,
            'phone': phone,
            'location': location,
            'linkedin': linkedin,
            'job_title': job_title,
            'skills': skills,
            'summary': professional_summary
        }
        st.success("✅ Basic information saved!")

# Tab 2: Experience, Education, Projects
with tab2:
    st.header("Work Experience")
    
    num_jobs = st.number_input("How many jobs to add?", min_value=1, max_value=10, value=1)
    
    experiences = []
    for i in range(num_jobs):
        with st.expander(f"Job #{i+1}", expanded=(i==0)):
            job_title_input = st.text_input(f"Job Title", key=f"job_title_{i}")
            company = st.text_input(f"Company Name", key=f"company_{i}")
            
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.text_input(f"Start Date", placeholder="MM/YYYY", key=f"start_{i}")
            with col2:
                end_date = st.text_input(f"End Date", placeholder="MM/YYYY or Present", key=f"end_{i}")
            
            responsibilities = st.text_area(
                f"Key Responsibilities (one per line)",
                key=f"resp_{i}",
                height=100
            )
            
            experiences.append({
                'title': job_title_input,
                'company': company,
                'start': start_date,
                'end': end_date,
                'responsibilities': responsibilities
            })
    
    st.markdown("---")
    st.subheader("🎓 Education")
    
    num_edu = st.number_input("How many education entries?", min_value=1, max_value=5, value=1)
    
    education = []
    for i in range(num_edu):
        with st.expander(f"Education #{i+1}", expanded=(i==0)):
            degree = st.text_input(f"Degree", placeholder="B.S. Computer Science", key=f"degree_{i}")
            institution = st.text_input(f"Institution", key=f"institution_{i}")
            edu_year = st.text_input(f"Year", placeholder="2020", key=f"edu_year_{i}")
            
            education.append({
                'degree': degree,
                'institution': institution,
                'year': edu_year
            })
    
    st.markdown("---")
    st.subheader("🚀 Projects (Optional)")
    
    num_projects = st.number_input("How many projects?", min_value=0, max_value=10, value=0)
    
    projects = []
    for i in range(num_projects):
        with st.expander(f"Project #{i+1}", expanded=(i==0)):
            project_name = st.text_input(f"Project Name", key=f"project_name_{i}")
            project_desc = st.text_area(f"Project Description", key=f"project_desc_{i}", height=100)
            project_tech = st.text_input(f"Technologies Used", placeholder="React, Node.js, MongoDB", key=f"project_tech_{i}")
            
            projects.append({
                'name': project_name,
                'description': project_desc,
                'technologies': project_tech
            })
    
    if st.button("💾 Save All Information", type="primary"):
        st.session_state.resume_data['experience'] = experiences
        st.session_state.resume_data['education'] = education
        st.session_state.resume_data['projects'] = projects
        st.success("✅ All information saved!")

# Tab 3: Generate Resume
with tab3:
    st.header("📄 Generate Your Resume")
    
    if not st.session_state.resume_data.get('basic_info'):
        st.warning("⚠️ Please fill in your information in the previous tabs first!")
    else:
        st.success("✅ Ready to generate your resume!")
        
        with st.expander("👁️ Preview Your Data", expanded=False):
            st.json(st.session_state.resume_data)
        
        st.markdown("---")
        
        if st.button("🤖 Generate Resume with AI", type="primary", use_container_width=True):
            with st.spinner("✨ AI is crafting your professional resume..."):
                generated_resume = generate_resume_with_gemini(st.session_state.resume_data)
                
                if generated_resume.startswith("Error:"):
                    st.error(generated_resume)
                else:
                    st.session_state.generated_resume = generated_resume
                    
                    # Auto-save to Firebase if user email is provided
                    if user_email:
                        save_id = save_resume_to_firebase(db, st.session_state.resume_data, generated_resume, user_email)
                        if save_id:
                            st.success("✅ Resume generated and saved to Firebase!")
                    else:
                        st.success("✅ Resume generated successfully!")
                    
                    st.rerun()
        
        # Display generated resume
        if 'generated_resume' in st.session_state and st.session_state.generated_resume:
            st.markdown("---")
            st.subheader("📝 Your AI-Generated Resume")
            
            st.markdown(st.session_state.generated_resume)
            
            st.markdown("---")
            
            # Template selection for PDF
            st.subheader("📄 Download Your Resume")
            
            template_choice = st.selectbox(
                "Choose PDF Template Style",
                ["modern", "classic", "creative", "minimal"],
                format_func=lambda x: {
                    "modern": "🔵 Modern - Bold & Professional",
                    "classic": "⚫ Classic - Traditional & Formal",
                    "creative": "🟣 Creative - Unique & Colorful",
                    "minimal": "⚪ Minimal - Clean & Simple"
                }[x]
            )
            
            template_descriptions = {
                "modern": "Blue accents, bold headers, contemporary design",
                "classic": "Black text, serif font, traditional business format",
                "creative": "Purple theme, eye-catching, great for creative roles",
                "minimal": "Simple gray tones, maximum readability, ATS-optimized"
            }
            st.info(f"ℹ️ {template_descriptions[template_choice]}")
            
            # Download buttons
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.download_button(
                    label="📥 Download as Text",
                    data=st.session_state.generated_resume,
                    file_name=f"{st.session_state.resume_data.get('basic_info', {}).get('name', 'resume').replace(' ', '_')}_resume.txt",
                    mime="text/plain",
                    use_container_width=True
                )
            
            with col2:
                st.download_button(
                    label="📥 Download as Markdown",
                    data=st.session_state.generated_resume,
                    file_name=f"{st.session_state.resume_data.get('basic_info', {}).get('name', 'resume').replace(' ', '_')}_resume.md",
                    mime="text/markdown",
                    use_container_width=True
                )
            
            with col3:
                pdf_buffer = create_professional_pdf(
                    st.session_state.resume_data,
                    st.session_state.generated_resume,
                    template_choice
                )
                
                st.download_button(
                    label="📄 Download as PDF",
                    data=pdf_buffer,
                    file_name=f"{st.session_state.resume_data.get('basic_info', {}).get('name', 'resume').replace(' ', '_')}_resume.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    type="primary"
                )