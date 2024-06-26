<script setup lang="ts">
import { onMounted, ref, onBeforeMount } from 'vue'
import { extract_value, type ValueAndValidation } from '@/types'
import DForm from './DForm.vue'
import { clicked_checkbox_label } from '@/utils'
import type { VueDictionary, VueDictionaryElement } from '@/vue_types'

const emit = defineEmits<{
  (e: 'update-value', value: any): void
}>()

interface ElementFromProps {
  dict_config: VueDictionaryElement
  is_active: boolean
  data: any
}

const props = defineProps<{
  vue_schema: VueDictionary
  data: ValueAndValidation
}>()

let component_value: { [name: string]: any } = {}
const default_values = ref<any>({})
const element_components = ref<{ [index: string]: any }>({})
const element_active: { [index: string]: any } = ref({})

onBeforeMount(() => {
  component_value = {}
  console.log('dict schema', props.vue_schema)
  console.log('dict data', props.data)
  const data = extract_value(props.data)
  props.vue_schema.elements.forEach((element: VueDictionaryElement) => {
    const key = element.ident
    default_values.value[key] = element.default_value
    if (key in data) component_value[key] = data[key]
    else if (element.required) component_value[key] = element.default_value
    else component_value[key] = undefined
  })
})

onMounted(() => {
  emit('update-value', component_value)
})

function get_elements_from_props(): ElementFromProps[] {
  const elements: ElementFromProps[] = []
  const data = extract_value(props.data)
  props.vue_schema.elements.forEach((element: VueDictionaryElement, index: number) => {
    elements.push({
      dict_config: element,
      is_active:
        element.ident in element_active.value
          ? element_active.value[element.ident]
          : element.required,
      data: element.ident in data ? data[element.ident] : default_values.value[element.ident]
    })
  })
  return elements
}

function update_key(key: string, new_value: any) {
  component_value[key] = new_value
  emit('update-value', component_value)
}

function clicked_dictionary_checkbox_label(event: MouseEvent, key: string) {
  let target = event.target
  if (!target) return

  clicked_checkbox_label(target as HTMLLabelElement)

  const dict_values = extract_value(props.data)
  if (key in dict_values) component_value[key] = undefined
  else component_value[key] = dict_values[key]
  emit('update-value', component_value)
}
</script>

<template>
  <table class="dictionary">
    <tbody>
      <tr
        v-for="dict_element in get_elements_from_props()"
        v-bind:key="dict_element.dict_config.ident"
      >
        <td class="dictleft">
          <span class="checkbox">
            <input
              type="checkbox"
              v-model="element_active[dict_element.dict_config.ident]"
              v-if="!dict_element.dict_config.required"
            />
            <label
              :onclick="
                (event: MouseEvent) =>
                  clicked_dictionary_checkbox_label(event, dict_element.dict_config.ident)
              "
            >
              {{ dict_element.dict_config.vue_schema.title }}
            </label>
          </span>
          <br />
          <div class="dictelement indent">
            <DForm
              v-if="dict_element.is_active"
              :vue_schema="dict_element.dict_config.vue_schema"
              :data="dict_element.data"
              :ref="
                (el) => {
                  element_components[dict_element.dict_config.ident] = el
                }
              "
              @update-value="(new_value) => update_key(dict_element.dict_config.ident, new_value)"
            />
          </div>
        </td>
      </tr>
    </tbody>
  </table>
</template>
