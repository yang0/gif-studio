# A-roll 多视角与角色一致性

A-roll 负责主讲人、角色行动、情绪和故事。它不必使用 GIF，可以使用真实录制素材。B-roll 则解释知识和提供证据。
视觉编排支持 viewpoint=main_character、supporting_character、presenter、first_person。配角必须填 character_id。
camera_preset 可选 native、wide、presenter、medium、closeup、reaction。非 native 只是对真正已有画面的景别裁切，并非从另一个机位重新拍摄。
第一人称视角必须使用真实 POV 画面，指定 role=point_of_view、viewpoint=first_person、source_perspective=verified_first_person，且 camera_preset=native；不允许用裁切普通人物镜头冒充第一人称。
同一个 character_id 在不同镜头里必须进行脸部、体型、发型、服装、道具和场景的人工检查。不同人物要明确作为不同角色或举例，不能假称为同一人的连续镜头。
角色三视图、笔触和场景参考可在 reference_pack.py 校验；参考图存在不等于生成工具真的消费了参考图。
