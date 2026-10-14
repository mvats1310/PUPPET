from pathlib import Path
import shutil, yaml
import numpy as np, pandas as pd
BASE=Path("data")
def make_trial(participant,condition,trial,noise_scale,extra_loop=False):
    trial_dir=BASE/f"{participant}_{condition}_T{trial:02d}"; trial_dir.mkdir(parents=True,exist_ok=True)
    metadata={"participant_id":participant,"condition":condition,"trial_id":f"T{trial:02d}","training_group":"basic","task_name":"table_to_shelf_pick_place","task_success":True,"technician_intervention":False,"notes":"","video":{"vr_pov":"vr_pov_video.mp4","external":"external_camera_video.mp4"},"data":{"telemetry_csv":"telemetry.csv","rosbag":"robot_data.bag","optitrack_csv":"optitrack.csv"}}
    with (trial_dir/"metadata.yaml").open("w") as f: yaml.safe_dump(metadata,f)
    t=np.linspace(0,10,101); x=0.4+0.3*(t/10); y=0.1+0.1*(t/10); z=0.8+0.4*(t/10)
    if extra_loop: y += 0.08*np.sin(2*np.pi*t/3); z += 0.05*np.sin(2*np.pi*t/2)
    rng=np.random.default_rng(seed=trial*100+len(participant)+len(condition)); x+=rng.normal(0,noise_scale,len(t)); y+=rng.normal(0,noise_scale,len(t)); z+=rng.normal(0,noise_scale,len(t))
    data={"time":t,"ee_x":x,"ee_y":y,"ee_z":z}
    for j in range(1,8): data[f"joint_{j}"]=0.1*j+0.05*j*(t/10)+rng.normal(0,noise_scale,len(t))
    grip=np.array(["open"]*len(t),dtype=object); grip[t>3]="closed"; grip[t>8]="open"; data["gripper_state"]=grip
    pd.DataFrame(data).to_csv(trial_dir/"telemetry.csv",index=False)
    (trial_dir/"vr_pov_video.mp4").write_text("placeholder"); (trial_dir/"external_camera_video.mp4").write_text("placeholder")
def main():
    if BASE.exists(): shutil.rmtree(BASE)
    BASE.mkdir()
    for participant in ["P001","P002"]:
        for condition in ["VR","IN_PERSON"]:
            for trial in range(1,4): make_trial(participant,condition,trial,0.002,False)
    for participant in ["P003","P004"]:
        for condition in ["2D","VR"]:
            for trial in range(1,4): make_trial(participant,condition,trial,0.01*trial,trial%2==0)
    print("Sample dataset created in ./data")
if __name__=="__main__": main()
