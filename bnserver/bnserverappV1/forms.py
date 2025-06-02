from django import forms

class UploadFileForm(forms.Form):
    title = forms.CharField(max_length=50)
    file = forms.FileField()

def handle_uploaded_file(f):
    """
    Handles the uploaded file by writing its content to a specified destination.
    Parameters:
    ----------
    f : UploadedFile
        The file object to be processed.
    """
    with open("some/file/name.txt", "wb+") as destination:
        for chunk in f.chunks():
            destination.write(chunk)