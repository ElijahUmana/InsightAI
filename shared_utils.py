from PIL import Image

def png2pdf(png, output_path):
    """
    returns pdf file path
    """
    image_1 = Image.open(f'{png}')
    im_1 = image_1.convert('RGB')
    im_1.save(f'{output_path}.pdf')