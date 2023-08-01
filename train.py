import os
import time
import wandb
from pathlib import Path

import torch.nn as nn
import torch.utils.data
import torchvision.utils as vutils
from lightning.fabric import Fabric, seed_everything

from PIL import Image
from torchvision import transforms


import models
import data_utils
import train 
import optimizers
import loss
import numpy as np
from utils.opt import get_cfgs

torch.set_float32_matmul_precision("medium")

def main(cfgs: dict): 
    # Set random seed for reproduceability
    seed_everything(cfgs.seed)
    if cfgs.use_mixed_precision: 
        fabric = Fabric(accelerator="auto", devices = cfgs.gpus, precision="bf16-mixed")
    else: 
        fabric = Fabric(accelerator="auto", devices = cfgs.gpus)
    fabric.launch()

    if cfgs.use_wandb and fabric.is_global_zero:
        # WandB – Initialize a new run
        wandb.init(project=cfgs.wandb_project, config=cfgs)
        wandb.run.name = cfgs.wandb_run_name
        wandb.run.save()

    # create the dataset and dataloader 
    train_dataset, val_dataset, train_loader, val_loader = data_utils.get_dataset_and_dataloader(cfgs)
    
    # Shape: batch_size, modalities, triplet, channels, height, width
    train_loader, val_loader = fabric.setup_dataloaders(train_loader, val_loader)

    dataset_size = len(train_dataset) + len(val_dataset)

    if fabric.is_global_zero: 
        print("Dataset size total:", dataset_size)
        print("Training set size:", len(train_dataset))
        print("Validation set size:", len(val_dataset))

    # create output directory
    config_name = os.path.splitext(os.path.basename(cfgs.cfg_name))[0]
    unique_dir_name = time.strftime("%Y%m%d-%H%M%S-") + config_name

    output_dir = Path(cfgs.output_dir, unique_dir_name)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Output directory:", output_dir)

    # Get the model
    model = models.get_model(cfgs=cfgs, fabric=fabric)


    if cfgs.use_wandb and fabric.is_global_zero:
        # WandB – Watch the model
        wandb.watch(model)

    criterion = loss.get_loss(cfgs, fabric)

    optimizer = optimizers.get_optim(cfgs, model)

    trainer = train.get_trainer(cfgs, fabric, model, train_loader, val_loader, optimizer, criterion, unique_dir_name)

    # print out model summary
    if fabric.is_global_zero: 
        trainer.print_networks()

    # begin training
    if cfgs.phase == "train":
        trainer.train()
    elif cfgs.phase == "val":
        print(trainer.validate())

    # # if cfgs.show_ir_samples:
    # #     trainer.show_samples()
    
    

if __name__ == "__main__":
    cfgs = get_cfgs()
    if cfgs.output_dir: 
        Path(cfgs.output_dir).mkdir(parents=True, exist_ok=True)
    main(cfgs)