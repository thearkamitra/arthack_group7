using System;
using System.Collections.Generic;
using UnityEngine;

namespace InnerLandscape
{
    // All persisted coordinates have top-left origin. Never store head poses.
    public sealed class RegionAttention
    {
        [Serializable] public class Cell { public float seconds, x, y; }
        [Serializable] public class Decision
        {
            public int cycle; public string source_hash, input_mode;
            public float speaking_seconds; public string[] window_ids; public Cell[] cells;
        }
        readonly float[] dwell = new float[9], xs = new float[9], ys = new float[9];
        readonly List<string> windows = new List<string>();
        public float SpeakingSeconds { get; private set; }
        public float ValidSeconds { get { float total=0;foreach(var s in dwell)total+=s;return total; } }
        public float Percentage(int cell) => ValidSeconds>0?dwell[cell]/ValidSeconds*100:0;
        public int Winner { get { int best=0;for(int i=1;i<9;i++)if(dwell[i]>dwell[best])best=i;return best; } }
        public void Sample(float dt, bool speaking, bool valid, Vector2 uv, string window)
        {
            if(SpeakingSeconds>=120)return;
            dt=Mathf.Min(dt,120-SpeakingSeconds);
            if(!speaking || dt<=0 || float.IsNaN(dt) || float.IsInfinity(dt))return;
            SpeakingSeconds+=dt;
            if(!windows.Contains(window))windows.Add(window);
            if(!valid || float.IsNaN(uv.x) || float.IsNaN(uv.y) || float.IsInfinity(uv.x) || float.IsInfinity(uv.y) || uv.x<0 || uv.x>1 || uv.y<0 || uv.y>1)return;
            float x=uv.x,y=1-uv.y;
            int cell=Mathf.Min(2,(int)(x*3))+3*Mathf.Min(2,(int)(y*3));
            dwell[cell]+=dt;xs[cell]+=x*dt;ys[cell]+=y*dt;
        }
        public Decision Freeze(int cycle,string hash,string mode)
        {
            if(ValidSeconds<.5f)throw new InvalidOperationException("At least 0.5s valid guide-speaking attention required");
            var cells=new Cell[9];for(int i=0;i<9;i++)cells[i]=new Cell{seconds=dwell[i],x=dwell[i]>0?xs[i]/dwell[i]:(i%3+.5f)/3,y=dwell[i]>0?ys[i]/dwell[i]:(i/3+.5f)/3};
            return new Decision{cycle=cycle,source_hash=hash,input_mode=mode,speaking_seconds=SpeakingSeconds,window_ids=windows.ToArray(),cells=cells};
        }
    }
}
