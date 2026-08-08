from PIL import Image, ImageDraw, ImageFont

def create_canvas():
    background = Image.new(mode = "RGB", size = (1200, 1600), color = (103, 190, 217))
    background.show()

if __name__ == "__main__":
    create_canvas()