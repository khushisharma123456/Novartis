"""
Quality Agent Service - AI Agent Orchestration (STEP 10)
Manages agents that improve case quality by requesting targeted information
"""

from models import db, CaseAgent, FollowUp, User
from datetime import datetime


class QualityAgentOrchestrator:
    """
    Orchestrates AI agents to improve case quality through targeted questions
    Agents: Patient Agent (symptom clarity), Doctor Agent (medical confirmation), Hospital Agent (clinical records)
    """
    
    # Agent configurations with their roles and targeted questions
    AGENT_CONFIGS = {
        'patient': {
            'role': 'Patient Symptom Clarity Agent',
            'questions': [
                'Can you describe your exact symptoms in detail?',
                'When exactly did your symptoms start? (Date and time)',
                'When did your symptoms resolve or improve?',
                'Did you visit a doctor for these symptoms?',
                'Have you taken any other medications recently?',
                'Do you have any pre-existing medical conditions?',
                'Any family history of similar reactions?'
            ]
        },
        'doctor': {
            'role': 'Doctor Medical Confirmation Agent',
            'questions': [
                'Can you clinically confirm this adverse event?',
                'What is your professional medical assessment?',
                'Are there any relevant medical history details we should know?',
                'What treatment or intervention did you recommend?',
                'What follow-up do you recommend for this patient?',
                'In your clinical opinion, what is the severity of this reaction?'
            ]
        },
        'hospital': {
            'role': 'Hospital Clinical Records Agent',
            'questions': [
                'Are there hospital records confirming this adverse event?',
                'What diagnostic tests or lab results are available?',
                'Are there imaging or other diagnostic confirmations?',
                'What clinical notes document this case?',
                'Has the patient had any hospital admissions related to this?',
                'What is the clinical outcome documented in records?'
            ]
        }
    }
    
    def activate_agents(self, case, followup_info):
        """
        Activate appropriate agents based on case needs
        
        Args:
            case: Patient model instance
            followup_info: dict with triggers and priority from check_followup
            
        Returns:
            dict: {
                'agents_activated': [list of activated agents],
                'total_agents': int,
                'total_questions': int
            }
        """
        triggers = followup_info.get('triggers', [])
        activated_agents = []
        
        # Activate Patient Agent for incomplete data or symptom clarity
        if 'low_completeness' in triggers or 'unclear_score' in triggers:
            if case.created_by:  # Patient created the case
                agent = self._create_agent(case.id, 'patient', case.created_by)
                if agent:
                    activated_agents.append(agent)
        
        # Activate Doctor Agent for medical confirmation
        if 'no_medical_confirmation' in triggers or 'weak_ae' in triggers:
            if case.doctors and len(case.doctors) > 0:
                doctor = case.doctors[0]
                agent = self._create_agent(case.id, 'doctor', doctor.id)
                if agent:
                    activated_agents.append(agent)
        
        # Activate Hospital Agent for clinical records
        if case.recalled_by or (case.doctors and len(case.doctors) > 0):
            hospital_id = case.recalled_by or case.doctors[0].id
            agent = self._create_agent(case.id, 'hospital', hospital_id)
            if agent:
                activated_agents.append(agent)
        
        total_questions = sum(len(a.target_questions) if a.target_questions else 0 
                            for a in activated_agents)
        
        return {
            'success': True,
            'agents_activated': [self._agent_to_dict(a) for a in activated_agents],
            'total_agents': len(activated_agents),
            'total_questions': total_questions
        }
    
    def _create_agent(self, case_id, agent_type, recipient_id):
        """
        Create and activate a quality agent
        
        Args:
            case_id: Patient ID
            agent_type: 'patient'|'doctor'|'hospital'
            recipient_id: User ID to send questions to
            
        Returns:
            CaseAgent instance
        """
        config = self.AGENT_CONFIGS.get(agent_type)
        if not config:
            return None
        
        # Check if agent already exists and is active
        existing_agent = CaseAgent.query.filter_by(
            case_id=case_id,
            agent_type=agent_type,
            status='active'
        ).first()
        
        if existing_agent:
            return existing_agent
        
        # Create new agent
        agent = CaseAgent(
            case_id=case_id,
            agent_type=agent_type,
            role=config['role'],
            target_questions=config['questions'],
            recipient_id=recipient_id,
            status='active',
            created_at=datetime.utcnow()
        )
        
        db.session.add(agent)
        db.session.commit()
        
        return agent
    
    def _agent_to_dict(self, agent):
        """Convert agent to dictionary"""
        return {
            'id': agent.id,
            'type': agent.agent_type,
            'role': agent.role,
            'status': agent.status,
            'total_questions': len(agent.target_questions) if agent.target_questions else 0,
            'questions': agent.target_questions,
            'recipient_id': agent.recipient_id,
            'created_at': agent.created_at.isoformat() if agent.created_at else None
        }
    
    def get_agent_questions(self, agent_id):
        """
        Get targeted questions for an agent
        
        Returns human-readable agent message with questions
        """
        agent = CaseAgent.query.get(agent_id)
        if not agent:
            return None
        
        questions = agent.target_questions or []
        
        message = f"""
Hello! We're improving our pharmacovigilance case {agent.case_id}.

As {agent.role}, we need your help with the following questions:

"""
        for i, question in enumerate(questions, 1):
            message += f"{i}. {question}\n"
        
        message += """
Your responses will help us better assess this case.
Please reply with your answers.

Thank you!
"""
        
        return message
    
    def submit_agent_response(self, agent_id, responses):
        """
        Submit responses to an agent's questions
        
        Args:
            agent_id: ID of the agent
            responses: dict or list of responses
            
        Returns:
            dict with success status
        """
        agent = CaseAgent.query.get(agent_id)
        if not agent:
            return {'success': False, 'message': 'Agent not found'}
        
        # Store responses
        agent.responses = responses
        agent.status = 'completed'
        agent.resolved_at = datetime.utcnow()
        
        db.session.commit()
        
        # Update case as having received follow-up response
        case = agent.case
        case.follow_up_response = str(responses)
        case.follow_up_sent = True
        
        db.session.commit()
        
        return {
            'success': True,
            'message': f'Agent {agent.id} response recorded',
            'agent_id': agent_id
        }
    
    def get_active_agents_for_case(self, case_id):
        """Get all active agents for a case"""
        agents = CaseAgent.query.filter_by(
            case_id=case_id,
            status='active'
        ).all()
        
        return {
            'case_id': case_id,
            'active_agents': len(agents),
            'agents': [self._agent_to_dict(a) for a in agents]
        }


class FollowUpManager:
    """
    Manages follow-up requests and tracking
    """
    
    def create_followup(self, case_id, reason, priority='medium', assigned_to=None):
        """
        Create a follow-up request for a case
        
        Args:
            case_id: Patient ID
            reason: Why follow-up is needed
            priority: 'low'|'medium'|'high'|'critical'
            assigned_to: User ID to assign follow-up to
            
        Returns:
            FollowUp instance
        """
        followup = FollowUp(
            case_id=case_id,
            reason=reason,
            priority=priority,
            assigned_to=assigned_to,
            status='pending',
            created_at=datetime.utcnow()
        )
        
        db.session.add(followup)
        db.session.commit()
        
        return followup
    
    def get_followups_for_case(self, case_id, status=None):
        """Get follow-ups for a case"""
        query = FollowUp.query.filter_by(case_id=case_id)
        
        if status:
            query = query.filter_by(status=status)
        
        followups = query.order_by(FollowUp.created_at.desc()).all()
        
        return [self._followup_to_dict(f) for f in followups]
    
    def update_followup(self, followup_id, status=None, response=None):
        """Update follow-up status and response"""
        followup = FollowUp.query.get(followup_id)
        if not followup:
            return {'success': False, 'message': 'Follow-up not found'}
        
        if status:
            followup.status = status
        
        if response:
            followup.response = response
        
        if status == 'resolved':
            followup.resolved_at = datetime.utcnow()
        
        db.session.commit()
        
        return {'success': True, 'followup_id': followup_id}
    
    def _followup_to_dict(self, followup):
        """Convert follow-up to dictionary"""
        return {
            'id': followup.id,
            'case_id': followup.case_id,
            'reason': followup.reason,
            'status': followup.status,
            'priority': followup.priority,
            'assigned_to': followup.assigned_to,
            'assigned_user': followup.assigned_user.name if followup.assigned_user else None,
            'created_at': followup.created_at.isoformat() if followup.created_at else None,
            'resolved_at': followup.resolved_at.isoformat() if followup.resolved_at else None,
            'response': followup.response
        }
    
    def get_pending_followups(self, user_id=None):
        """Get all pending follow-ups, optionally filtered by assigned user"""
        query = FollowUp.query.filter_by(status='pending')
        
        if user_id:
            query = query.filter_by(assigned_to=user_id)
        
        followups = query.order_by(FollowUp.priority.desc()).all()
        
        return [self._followup_to_dict(f) for f in followups]


# Utility functions

def activate_quality_agents(case, followup_info):
    """Convenience function to activate agents"""
    orchestrator = QualityAgentOrchestrator()
    return orchestrator.activate_agents(case, followup_info)


def create_followup_request(case_id, reason, priority='medium'):
    """Convenience function to create follow-up"""
    manager = FollowUpManager()
    return manager.create_followup(case_id, reason, priority)
