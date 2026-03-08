import os
from PIL import Image, ImageDraw

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")

class BoardRenderer:
    def __init__(self):
        self.board_img = Image.open(os.path.join(ASSETS_DIR, "board_neon.png")).convert("RGBA")
        self.board_xo = Image.open(os.path.join(ASSETS_DIR, "board_xo.png")).convert("RGBA")
        self.pieces_checkers = Image.open(os.path.join(ASSETS_DIR, "pieces_checkers.png")).convert("RGBA")
        self.pieces_chess = Image.open(os.path.join(ASSETS_DIR, "pieces_chess.png")).convert("RGBA")
        self.pieces_xo = Image.open(os.path.join(ASSETS_DIR, "pieces_xo.png")).convert("RGBA")
        
        # Default properties (8x8)
        self.size = self.board_img.size[0]
        self.cell_size = self.size // 8
        
    def _get_checkers_piece(self, p_type: str) -> Image.Image:
        """
        Types: r_man, b_man, r_king, b_king
        Piece sheet is assumed to be 2x2.
        """
        w, h = self.pieces_checkers.size
        pw, ph = w // 2, h // 2
        coords = {
            "r_man": (0, 0),
            "b_man": (1, 0),
            "r_king": (0, 1),
            "b_king": (1, 1),
        }
        x, y = coords.get(p_type, (0, 0))
        piece = self.pieces_checkers.crop((x * pw, y * ph, (x + 1) * pw, (y + 1) * ph))
        return piece.resize((self.cell_size, self.cell_size), Image.LANCZOS)

    def _get_chess_piece(self, p_type: str, color: str) -> Image.Image:
        """
        p_type: K, Q, R, B, N, P
        color: white, violet
        Piece sheet: 6 columns (K, Q, R, B, N, P), 2+ rows (color)
        """
        w, h = self.pieces_chess.size
        pw, ph = w // 6, h // 4 # High res sheet has multiple rows, we use top 2
        types = ["K", "Q", "R", "B", "N", "P"]
        try:
            col = types.index(p_type.upper())
        except ValueError:
            col = 5 # Pawn fallback
        
        row = 0 if color == "white" else 2 # Based on the generated sheet
        
        piece = self.pieces_chess.crop((col * pw, row * ph, (col + 1) * pw, (row + 1) * ph))
        return piece.resize((self.cell_size, self.cell_size), Image.LANCZOS)

    def _get_wallpaper(self, wp_name: str) -> Image.Image | None:
        if not wp_name or wp_name == "default":
            return None
        path = os.path.join(ASSETS_DIR, f"wallpaper_{wp_name}.png")
        if os.path.exists(path):
            return Image.open(path).convert("RGBA")
        return None

    def _apply_wallpaper(self, canvas: Image.Image, wp_name: str) -> Image.Image:
        wp = self._get_wallpaper(wp_name)
        if not wp:
            return canvas
        # Scale wallpaper to cover or fit? Usually cover is better for aesthetic.
        # But for board, we can just center/crop or stretch.
        wp = wp.resize(canvas.size, Image.LANCZOS)
        # We can blend it or just put it under. 
        # If canvas has transparency, wp will show through.
        # Most backgrounds are solid, so we might need to make canvas semi-transparent or blend.
        # Let's try blending with 0.7 alpha for the board if wallpaper is present.
        return Image.alpha_composite(wp, canvas)

    def render_checkers(self, board, selected=None, valid_moves=None, wallpaper: str = "default") -> Image.Image:
        """
        board: 8x8 nested list or similar
        """
        canvas = self.board_img.copy()
        
        # If wallpaper is set, we might want to make board semi-transparent
        if wallpaper and wallpaper != "default":
            # Make board 85% opaque to see wallpaper
            alpha = canvas.getchannel('A')
            alpha = alpha.point(lambda p: int(p * 0.85))
            canvas.putalpha(alpha)
            canvas = self._apply_wallpaper(canvas, wallpaper)

        draw = ImageDraw.Draw(canvas)
        
        # Highlight selected
        if selected:
            r, c = selected
            x, y = c * self.cell_size, r * self.cell_size
            draw.rectangle([x, y, x + self.cell_size, y + self.cell_size], outline="yellow", width=5)
            
        # Highlight valid moves
        if valid_moves:
            for r, c in valid_moves:
                x, y = c * self.cell_size, r * self.cell_size
                draw.ellipse([x + 20, y + 20, x + self.cell_size - 20, y + self.cell_size - 20], fill=(0, 255, 0, 100))

        for r in range(8):
            for c in range(8):
                v = board[r][c]
                if v == 0: continue
                
                p_key = None
                if v == 1: p_key = "r_man"
                elif v == 2: p_key = "b_man"
                elif v == 11: p_key = "r_king"
                elif v == 22: p_key = "b_king"
                
                if p_key:
                    piece = self._get_checkers_piece(p_key)
                    canvas.alpha_composite(piece, (c * self.cell_size, r * self.cell_size))
                    
        return canvas

    def render_chess(self, board_dict, selected=None, valid_moves=None, wallpaper: str = "default") -> Image.Image:
        """
        board_dict: {(r, c): (piece_char, color)}
        """
        canvas = self.board_img.copy()
        if wallpaper and wallpaper != "default":
            alpha = canvas.getchannel('A')
            alpha = alpha.point(lambda p: int(p * 0.85))
            canvas.putalpha(alpha)
            canvas = self._apply_wallpaper(canvas, wallpaper)

        draw = ImageDraw.Draw(canvas)
        
        if selected:
            r, c = selected
            x, y = c * self.cell_size, r * self.cell_size
            draw.rectangle([x, y, x + self.cell_size, y + self.cell_size], outline="yellow", width=5)

        for (r, c), (p_char, color) in board_dict.items():
            piece = self._get_chess_piece(p_char, color)
            canvas.alpha_composite(piece, (c * self.cell_size, r * self.cell_size))
            
        return canvas
    
    def render_xo(self, board_str: str, highlight: set[int] = None, wallpaper: str = "default") -> Image.Image:
        """
        board_str: e.g. "X.O...X.." (9 chars)
        """
        canvas = self.board_xo.copy()
        if wallpaper and wallpaper != "default":
            # For XO, the board is usually very transparent/minimal, so we can just put it on top of wallpaper
            canvas = self._apply_wallpaper(canvas, wallpaper)

        draw = ImageDraw.Draw(canvas)
        size = canvas.size[0]
        cell_size = size // 3
        
        w_p, h_p = self.pieces_xo.size
        pw = w_p // 2
        
        # Crop and resize
        x_piece = self.pieces_xo.crop((0, 0, pw, h_p)).resize((cell_size, cell_size), Image.LANCZOS)
        o_piece = self.pieces_xo.crop((pw, 0, w_p, h_p)).resize((cell_size, cell_size), Image.LANCZOS)
        
        for i, char in enumerate(board_str):
            if i >= 9: break
            if char in (".", " ", "0"): continue
            
            r, c = i // 3, i % 3
            pos = (c * cell_size, r * cell_size)
            if char.upper() == "X":
                canvas.alpha_composite(x_piece, pos)
            elif char.upper() == "O":
                canvas.alpha_composite(o_piece, pos)
                
        if highlight:
            for i in highlight:
                if i < 0 or i >= 9: continue
                r, c = i // 3, i % 3
                x, y = c * cell_size, r * cell_size
                draw.rectangle([x, y, x + cell_size, y + cell_size], outline="yellow", width=8)
                
        return canvas

renderer = BoardRenderer()
