import torch
import torch.nn as nn

class TransformerDecoder(nn.Module):
    '''
    Transformer Decoder class to be leveraged for decoding the target token sequences
    based on encoded memory representations from the encoder.
    '''
    def __init__(self,
                 d_model: int = 512,
                 nhead: int = 8,
                 dim_feedforward: int = 2048,
                 dropout: float = 0.1,
                 n_layers: int = 6):
        super(TransformerDecoder, self).__init__()
        self.decoder_layer = nn.TransformerDecoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=dim_feedforward,
            dropout=dropout,
            batch_first=True,
            norm_first=True
        )
        self.transformer_decoder = nn.TransformerDecoder(
            self.decoder_layer,
            num_layers=n_layers
        )

    def forward(self,
                target_tokens,
                memory,
                tgt_mask=None,
                memory_mask=None,
                tgt_key_padding_mask=None,
                memory_key_padding_mask=None):
        out = self.transformer_decoder(
            tgt=target_tokens,
            memory=memory,
            tgt_mask=tgt_mask,
            memory_mask=memory_mask,
            tgt_key_padding_mask=tgt_key_padding_mask,
            memory_key_padding_mask=memory_key_padding_mask
        )
        return out
    

class CNNDecoder(nn.Module):
    def __init__(self, embed_dim, img_height, img_width):
        """
        Args:
            embed_dim (int): Number of channels from the transformer decoder.
            img_height (int): The target image height (H).
            img_width (int): The target image width (W).
        
        Note:
            The transformer output has a shape of (batch, (H*W)/64, embed_dim).
            This implies that when the features are reshaped into a grid,
            the grid size will be (H/8) x (W/8), since (H*W/64) = (H/8)*(W/8).
        """
        super(CNNDecoder, self).__init__()
        self.img_height = img_height
        self.img_width = img_width

        # Calculate grid dimensions (m = 8)
        self.grid_h = img_height // 8
        self.grid_w = img_width // 8
        
        # First layer: maintains embed_dim channels; upscales by 2.
        self.layer1 = nn.Sequential(
            nn.Conv2d(embed_dim, embed_dim, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
            nn.Upsample(scale_factor=2, mode='nearest')
        )
        
        # Second layer: maintains embed_dim channels; upscales by 2.
        self.layer2 = nn.Sequential(
            nn.Conv2d(embed_dim, embed_dim, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
            nn.Upsample(scale_factor=2, mode='nearest')
        )
        
        # Third layer: converts the feature channels from embed_dim to 3; upscales by 2.
        self.layer3 = nn.Sequential(
            nn.Conv2d(embed_dim, 3, kernel_size=3, padding=1),
            nn.ReLU(inplace=True),
            nn.Upsample(scale_factor=2, mode='nearest')
        )

    def forward(self, x):
        """
        Forward pass of the decoder.
        
        Args:
            x (torch.Tensor): Input tensor of shape (batch, (H*W)/64, embed_dim)
            
        Returns:
            torch.Tensor: Output tensor of shape (batch, 3, H, W)
        """
        batch_size, num_tokens, channels = x.shape
        
        # Reshape flattened tokens
        x = x.view(batch_size, self.grid_h, self.grid_w, channels)  # Shape: (batch, grid_h, grid_w, C)
        # Permute to channel-first format
        x = x.permute(0, 3, 1, 2)   # Shape: (batch, C, grid_h, grid_w)
        
        # Pass through the three-layer CNN decoder.
        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        
        return x    # Shape: (batch, 3, H, W)
