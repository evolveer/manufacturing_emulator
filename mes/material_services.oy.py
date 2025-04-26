# services/material_service.py
class MaterialService:
    _materials = {}  # in-memory store, replace with database if needed
    _id_counter = 1

    @classmethod
    def create_material(cls, material_data):
        material_id = cls._id_counter
        cls._id_counter += 1
        material_data['id'] = material_id
        cls._materials[material_id] = material_data
        return material_data

    @classmethod
    def get_all_materials(cls):
        return list(cls._materials.values())
