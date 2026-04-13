 ```mermaid
flowchart TD
       J0([J0<br/>Input DNG])

       S1["1. CLI ingress / validation<br/>1) core.main distinguishes management vs conversion<br/>2) run validates OS, path, dependencies, EXIF"]
       S2["2. Linear base extraction + RAW-WB normalization<br/>1) neutral rawpy.postprocess -> RGB uint16<br/>2) / sensor dynamic range -> RGB float32<br/>3) apply normalized WB gains (GREEN/MAX/MIN/MEAN)<br/>Output: J1 camera-linear RGB float32"]
       J1([J1<br/>camera-linear RGB float32<br/>WB applied])

       S3A["3/A Auto-brightness disabled<br/>pass-through"]
       S3B["3/B Auto-brightness enabled<br/>1) BT.709 luminance<br/>2) key selection / override<br/>3) Reinhard luminance mapping<br/>4) rescale RGB by luminance ratio<br/>5) optional overflow-only desaturation"]
       J2([J2<br/>camera-linear RGB float32<br/>post-AB])

       S4A["4/A Auto-WB disabled<br/>pass-through"]
       S4B["4/B-F Auto-WB enabled<br/>1) estimate a single gain vector<br/>2) modes: Simple / GrayworldWB / IA / ColorConstancy / TTL<br/>3) apply gains to the original camera-linear image"]
       J3([J3<br/>camera-linear RGB float32<br/>post-AWB])

       S5A["5/A auto ev_zero+delta<br/>1) ev_best / ev_ettr / ev_detail<br/>2) ev_zero = min(...)<br/>3) iterative ev_delta"]
       S5B["5/B auto ev_zero only<br/>1) ev_best / ev_ettr / ev_detail<br/>2) ev_zero = min(...)<br/>3) static ev_delta"]
       S5C["5/C auto ev_delta only<br/>1) static ev_zero<br/>2) iterative ev_delta<br/>3) OpenCV-Tonemap: fixed 0.1 EV"]
       S5D["5/D static<br/>1) static ev_zero<br/>2) static ev_delta"]

       S6["6/A-B Bracket synthesis<br/>1) 2^(ev_zero-delta), 2^ev_zero, 2^(ev_zero+ev_delta)<br/>2) EV scaling on the base image<br/>3) clip &#91;0,1&#93; per bracket<br/>4) if OpenCV-Tonemap: ev_zero only, side brackets=None"]
       J4([J4<br/>Bracket contract<br/>camera-linear RGB float32 &#91;0,1&#93;])

       S7A["7/A Luminance-HDR<br/>1) bracket -> TIFF32<br/>2) external luminance-hdr-cli merge+TMO<br/>3) TIFF32 -> RGB float normalized"]
       S7B["7/B OpenCV-Merge Debevec<br/>1) EXIF exposure times<br/>2) float32 radiance merge<br/>3) optional simple tonemap<br/>4) normalize &#91;0,1&#93;<br/>5) merge gamma"]
       S7C["7/C OpenCV-Merge Robertson<br/>1) EXIF exposure times<br/>2) float32 radiance merge<br/>3) optional simple tonemap<br/>4) normalize &#91;0,1&#93;<br/>5) merge gamma"]
       S7D["7/D OpenCV-Merge Mertens<br/>1) merge gamma on each bracket<br/>2) MergeMertens<br/>3) *255 bridge<br/>4) optional simple tonemap<br/>5) normalize &#91;0,1&#93;"]
       S7E["7/E OpenCV-Tonemap Drago<br/>1) use ev_zero only<br/>2) Drago tonemap (gamma_inv)<br/>3) merge gamma no-clip"]
       S7F["7/F OpenCV-Tonemap Reinhard<br/>1) use ev_zero only<br/>2) Reinhard tonemap (gamma_inv)<br/>3) merge gamma no-clip"]
       S7G["7/G OpenCV-Tonemap Mantiuk<br/>1) use ev_zero only<br/>2) Mantiuk tonemap (gamma_inv)<br/>3) merge gamma no-clip"]
       S7H["7/H HDR-Plus<br/>1) reorder (ev_zero, ev_minus, ev_plus)<br/>2) scalar proxy<br/>3) hierarchical alignment<br/>4) box_down2<br/>5) temporal merge<br/>6) spatial blend<br/>7) merge gamma"]

       J5([J5<br/>display-referred RGB float32<br/>backend output])

       S8["8. Postprocess entry adaptation<br/>1) float backend outputs pass-through<br/>2) non-float payloads only -> normalize to RGB float32"]
       J6([J6<br/>display-referred RGB float32<br/>postprocess entry])

       S9["9/A-B Static postprocess<br/>1) 9/A numeric: gamma -> brightness -> contrast -> saturation<br/>2) 9/B auto: LUT auto-gamma -> brightness -> contrast -> saturation<br/>3) only non-neutral substages execute"]
       J7([J7<br/>display-referred RGB float32<br/>post-static])

       S10["10/A-G Auto-levels<br/>10/A disabled: pass-through<br/>10/B enabled no HR<br/>10/C-G enabled + HR method {Luminance Recovery | CIELab Blending | Blend | Color Propagation | Inpaint Opposed}<br/>+ optional gamut clip"]
       J8([J8<br/>display-referred RGB float32<br/>post-auto-levels])

       S11["11/A-B Auto-adjust<br/>11/A disabled: pass-through<br/>11/B enabled: blur -> level -> CLAHE-luma -> sigmoid -> HSL vibrance -> high-pass overlay"]
       J9([J9<br/>display-referred RGB float32<br/>post-auto-adjust])

       S12["12. Final save prep + encode<br/>1) clip &#91;0,1&#93;<br/>2) quantize RGB uint8<br/>3) Pillow JPEG save<br/>4) EXIF thumbnail refresh if present"]
       J12([J12<br/>Output JPG])

       J0 --> S1 --> S2 --> J1
       J1 --> S3A --> J2
       J1 --> S3B --> J2
       J2 --> S4A --> J3
       J2 --> S4B --> J3

       J3 --> S5A --> S6
       J3 --> S5B --> S6
       J3 --> S5C --> S6
       J3 --> S5D --> S6

       S6 --> J4
       J4 --> S7A --> J5
       J4 --> S7B --> J5
       J4 --> S7C --> J5
       J4 --> S7D --> J5
       J4 --> S7E --> J5
       J4 --> S7F --> J5
       J4 --> S7G --> J5
       J4 --> S7H --> J5

       J5 --> S8 --> J6 --> S9 --> J7 --> S10 --> J8 --> S11 --> J9 --> S12 --> J12
```