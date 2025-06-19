from django.http import JsonResponse, HttpResponse, HttpRequest
from django.views.decorators.csrf import csrf_exempt
import json
from bnserverappV1.models import Questionnaire, Question, Answer, User
from bnserverappV1.auth import require_auth, require_admin, get_user_info, require_admin_token

@csrf_exempt
@require_admin
def create_questionnaire(request):
    """
    Create a new questionnaire.

    Endpoint: POST /create_questionnaire/

    Request Body:
    {
        "title": "Questionnaire Title",  # Required
        "description": "Optional description"  # Optional
    }

    Headers:
    - Authorization: Bearer <jwt_token>

    Returns:
    {
        "message": "Questionnaire created successfully",
        "questionnaire": {
            "id": 1,
            "title": "Questionnaire Title",
            "description": "Optional description",
            "created_at": "2024-04-13T12:00:00Z"
        }
    }
    """
    if request.method != 'POST':
        return JsonResponse({"error": "Only POST method is allowed"}, status=405)

    try:
        data = json.loads(request.body)
        title = data.get('title')
        description = data.get('description', '')

        if not title:
            return JsonResponse({"error": "Title is required"}, status=400)

        questionnaire = Questionnaire.objects.create(
            title=title,
            description=description
        )

        return JsonResponse({
            "message": "Questionnaire created successfully",
            "questionnaire": {
                "id": questionnaire.id,
                "title": questionnaire.title,
                "description": questionnaire.description,
                "created_at": questionnaire.created_at.isoformat()
            }
        }, status=201)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON format"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
@require_admin
def create_question(request):
    """
    Create a new question in a questionnaire.

    Endpoint: POST /create_question/

    Request Body:
    {
        "questionnaire_id": int,
        "text": "string",
        "question_type": "string",  # Optional, defaults to "text"
        "required": boolean         # Optional, defaults to false
    }

    Headers:
        Authorization: Bearer <jwt_token>

    Returns:
        JsonResponse: On success:
    {
        "message": "Question created successfully",
        "question": {
                    "id": int,
                    "questionnaire_id": int,
                    "text": "string",
                    "question_type": "string",
                    "required": boolean,
                    "created_at": "string"
        }
    }
    """
    if request.method != 'POST':
        return JsonResponse({"error": "Only POST method is allowed"}, status=405)

    try:
        data = json.loads(request.body)
        questionnaire_id = data.get('questionnaire_id')
        text = data.get('text')
        question_type = data.get('question_type', 'text')  # Default to 'text' if not specified
        required = data.get('required', False)  # Default to False if not specified

        if not all([questionnaire_id, text]):
            return JsonResponse({"error": "questionnaire_id and text are required"}, status=400)

        # Verify questionnaire exists
        questionnaire = Questionnaire.objects.get(id=questionnaire_id)

        question = Question.objects.create(
            questionnaire=questionnaire,
            text=text,
            question_type=question_type,
            required=required
        )

        return JsonResponse({
            "message": "Question created successfully",
            "question": {
                "id": question.id,
                "questionnaire_id": questionnaire_id,
                "text": question.text,
                "question_type": question.question_type,
                "required": question.required,
                "created_at": question.created_at.isoformat()
            }
        }, status=201)

    except Questionnaire.DoesNotExist:
        return JsonResponse({"error": "Questionnaire not found"}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON format"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
@require_auth
def submit_answers(request):
    """
    Submit answers to questionnaire questions.

    Endpoint: POST /submit_answers/

    Request Body:
    {
        "answers": [
            {
                "question_id": int,
                "answer_text": "string"
            },
            ...
        ]
    }

    Headers:
        Authorization: Bearer <jwt_token>

    Returns:
        JsonResponse: On success:
    {
        "message": "Answers submitted successfully",
        "saved_answers": [
            {
                        "question_id": int,
                        "answer_text": "string"
            },
                    ...
        ]
    }
    """
    if request.method != 'POST':
        return JsonResponse({"error": "Only POST method is allowed"}, status=405)

    try:
        data = json.loads(request.body)
        answers = data.get('answers', [])  # Expected format: [{"question_id": 1, "answer_text": "..."}, ...]

        if not answers:
            return JsonResponse({"error": "Missing answers"}, status=400)

        # Verify user exists
        user_id, role = get_user_info(request)
        user = User.objects.get(id=user_id)

        # Get all questions that are being answered
        question_ids = [answer.get('question_id') for answer in answers]
        questions = Question.objects.filter(id__in=question_ids)

        # Check if all required questions are answered and have non-empty answers
        required_questions = questions.filter(required=True)
        answered_question_ids = set(question_ids)
        missing_required = required_questions.exclude(id__in=answered_question_ids)

        # Check for empty answers on required questions
        empty_required = []
        for answer in answers:
            question_id = answer.get('question_id')
            answer_text = answer.get('answer_text', '')
            question = questions.filter(id=question_id, required=True).first()
            if question and len(str(answer_text).strip()) == 0:
                empty_required.append(question)

        if empty_required:
            missing_required = list(missing_required) + empty_required

        if missing_required.exists():
            missing_questions = [q.text for q in missing_required]
            return JsonResponse({
                "error": "Missing answers for required questions",
                "missing_questions": missing_questions
            }, status=400)

        # Process each answer
        saved_answers = []
        for answer_data in answers:
            question_id = answer_data.get('question_id')
            answer_text = answer_data.get('answer_text')

            if not question_id or not answer_text:
                continue

            # Verify question exists
            question = Question.objects.get(id=question_id)

            # Create and save answer
            answer = Answer.objects.create(
                question=question,
                user=user,
                answer_text=answer_text
            )
            saved_answers.append({
                "question_id": question_id,
                "answer_text": answer_text
            })

        return JsonResponse({
            "message": "Answers submitted successfully",
            "saved_answers": saved_answers
        }, status=201)

    except User.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=404)
    except Question.DoesNotExist:
        return JsonResponse({"error": "One or more questions not found"}, status=404)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON format"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
@require_admin
def get_answers_by_question(request):
    """
    Get all answers for a specific question.

    Endpoint: GET /get_answers/?question_id=1

    Query Parameters:
    - question_id: Required, the ID of the question

    Headers:
    - Authorization: Bearer <jwt_token>

    Returns:
    {
        "question_id": 1,
        "answers": [
            {
                "id": 1,
                "user_id": 1,
                "username": "user1",
                "answer_text": "Answer text",
                "created_at": "2024-04-13T12:00:00Z"
            },
            ...
        ]
    }
    """
    if request.method != 'GET':
        return JsonResponse({"error": "Only GET method is allowed"}, status=405)

    try:
        question_id = request.GET.get('question_id')
        if not question_id:
            return JsonResponse({"error": "question_id parameter is required"}, status=400)

        # Get all answers for the specified question
        answers = Answer.objects.filter(question_id=question_id)

        # Format the response
        answers_list = []
        for answer in answers:
            answers_list.append({
                "id": answer.id,
                "user_id": answer.user.id,
                "username": answer.user.username,
                "answer_text": answer.answer_text,
                "created_at": answer.created_at.isoformat()
            })

        return JsonResponse({
            "question_id": question_id,
            "answers": answers_list
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
@require_auth
def get_questions_by_questionnaire(request):
    """
    Get all questions for a specific questionnaire.

    Endpoint: GET /get_questions/?questionnaire_id=1

    Query Parameters:
        questionnaire_id: Required, the ID of the questionnaire

    Headers:
        Authorization: Bearer <jwt_token>

    Returns:
        JsonResponse: {
        "questionnaire": {
                "id": int,
                "title": "string",
                "description": "string"
        },
        "questions": [
            {
                    "id": int,
                    "text": "string",
                    "question_type": "string",
                    "required": boolean,
                    "created_at": "string"
            },
            ...
        ]
    }
    """
    if request.method != 'GET':
        return JsonResponse({"error": "Only GET method is allowed"}, status=405)

    try:
        questionnaire_id = request.GET.get('questionnaire_id')
        if not questionnaire_id:
            return JsonResponse({"error": "questionnaire_id parameter is required"}, status=400)

        # Get the questionnaire and its questions
        questionnaire = Questionnaire.objects.get(id=questionnaire_id)
        questions = Question.objects.filter(questionnaire=questionnaire)

        # Format the response
        questions_list = []
        for question in questions:
            questions_list.append({
                "id": question.id,
                "text": question.text,
                "question_type": question.question_type,
                "required": question.required,
                "created_at": question.created_at.isoformat()
            })

        return JsonResponse({
            "questionnaire": {
                "id": questionnaire.id,
                "title": questionnaire.title,
                "description": questionnaire.description
            },
            "questions": questions_list
        })

    except Questionnaire.DoesNotExist:
        return JsonResponse({"error": "Questionnaire not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
# @require_admin
def download_answers_csv(request: HttpRequest):
    """
    Download all answers for a questionnaire as a CSV file.

    Endpoint: GET /download_answers_csv/?questionnaire_id=1

    Query Parameters:
    - questionnaire_id: Required, the ID of the questionnaire

    Headers:
    - Authorization: Bearer <jwt_token>

    Returns:
    - A CSV file with tab delimiter where:
      - Each question is a column
      - Each row represents a user's set of answers
      - First row contains question texts as headers
    """
    if request.method != 'GET':
        return JsonResponse({"error": "Only GET method is allowed"}, status=405)

    try:
        questionnaire_id = request.GET.get('questionnaire_id')
        token = request.GET.get('token')

        if not require_admin_token(token):
            return JsonResponse({"error": "Invalid token"}, status=400)

        if not questionnaire_id:
            return JsonResponse({"error": "questionnaire_id parameter is required"}, status=400)

        # Get the questionnaire and its questions

        questionnaire = Questionnaire.objects.get(id=questionnaire_id)
        questions = Question.objects.filter(questionnaire=questionnaire).order_by('id')

        # Get all answers for these questions
        answers = Answer.objects.filter(question__in=questions).select_related('user', 'question')

        # Create a dictionary to organize answers by user
        user_answers = {}
        for answer in answers:
            if answer.user.id not in user_answers:
                user_answers[answer.user.id] = {
                    'username': answer.user.username,
                    'answers': {}
                }
            user_answers[answer.user.id]['answers'][answer.question.id] = answer.answer_text

        # Create CSV content
        import csv
        import io

        # Create a StringIO object to write CSV
        output = io.StringIO()
        writer = csv.writer(output, delimiter='\t')

        # Write header row with question texts
        header = ['Username'] + [q.text for q in questions]
        writer.writerow(header)

        # Write each user's answers
        for user_id, data in user_answers.items():
            row = [data['username']]
            for question in questions:
                row.append(data['answers'].get(question.id, ''))
            writer.writerow(row)

        # Create response with CSV file
        response = HttpResponse(output.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="questionnaire_{questionnaire_id}_answers.tsv"'

        return response

    except Questionnaire.DoesNotExist:
        return JsonResponse({"error": "Questionnaire not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)